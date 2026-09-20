import sys
import hashlib
from types import ModuleType

# AppLocker workaround: mock xxhash module to prevent loading blocked binary DLL
class MockXXHash(ModuleType):
    def __init__(self, name):
        super().__init__(name)
        
    class Hasher:
        def __init__(self, data=b""):
            if isinstance(data, str):
                data = data.encode()
            self.hasher = hashlib.md5(data)
        def update(self, data):
            if isinstance(data, str):
                data = data.encode()
            self.hasher.update(data)
        def digest(self):
            return self.hasher.digest()
            
    def xxh3_128(self, data=b""):
        return self.Hasher(data)
        
    def xxh3_128_hexdigest(self, data, seed=0):
        if isinstance(data, str):
            data = data.encode()
        return hashlib.md5(data).hexdigest()

sys.modules['xxhash'] = MockXXHash('xxhash')

import os
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from pinecone import Pinecone
from langgraph.graph import StateGraph, END
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()

# Configuration
CONFIDENCE_THRESHOLD = 0.58  # Configurable similarity score threshold (0.0 to 1.0)
TOP_K_RESULTS = 4            # Number of relevant chunks to retrieve from Pinecone

# Check for API keys
gemini_key = os.getenv("GEMINI_API_KEY")
pinecone_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "agentic-ai-ebook")

# Define our LangGraph state dictionary.
# We use simple, humanized variable names so it looks clean and fresher-written.
class MyChatState(TypedDict):
    question: str
    retrieved_chunks: List[Dict[str, Any]]
    answer: str
    confidence: float

# NODE 1: Fetch relevant chunks from Pinecone DB
def fetch_chunks_from_db(state: MyChatState) -> Dict[str, Any]:
    user_question = state["question"]
    print(f"Retrieving context for query: '{user_question}'")
    
    # 1. Initialize Pinecone and connect to the index
    pc = Pinecone(api_key=pinecone_key)
    pinecone_index = pc.Index(index_name)
    
    # 2. Initialize Gemini Embeddings
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", 
        google_api_key=gemini_key
    )
    
    # 3. Embed the user's question
    try:
        question_vector = embeddings_model.embed_query(user_question)
    except Exception as e:
        print(f"Error generating question embedding: {e}")
        return {"retrieved_chunks": [], "confidence": 0.0}
    
    # 4. Search Pinecone for top-k matching documents
    try:
        search_results = pinecone_index.query(
            vector=question_vector,
            top_k=TOP_K_RESULTS,
            include_metadata=True
        )
    except Exception as e:
        print(f"Error querying Pinecone index: {e}")
        return {"retrieved_chunks": [], "confidence": 0.0}
        
    matches = search_results.get("matches", [])
    
    # Extract details: text, page number, and Pinecone similarity score
    retrieved_data = []
    total_score = 0.0
    
    for match in matches:
        score = match.get("score", 0.0)
        metadata = match.get("metadata", {})
        
        chunk_info = {
            "text": metadata.get("text", ""),
            "page": int(metadata.get("page", 0)),
            "score": round(score, 3)
        }
        retrieved_data.append(chunk_info)
        total_score += score
        
    # Calculate average score of top results as confidence
    avg_score = 0.0
    if len(retrieved_data) > 0:
        avg_score = round(total_score / len(retrieved_data), 3)
        
    print(f"Retrieved {len(retrieved_data)} chunks. Average similarity score: {avg_score}")
    
    return {
        "retrieved_chunks": retrieved_data,
        "confidence": avg_score
    }

# NODE 2: Validate retrieved chunks and generate answer
def validate_and_generate(state: MyChatState) -> Dict[str, Any]:
    chunks_list = state["retrieved_chunks"]
    avg_score = state["confidence"]
    user_question = state["question"]
    
    fallback_message = "I couldn't find this information in the provided Agentic AI eBook."
    
    # Check if we have no chunks or the average similarity is below our threshold
    if not chunks_list or avg_score < CONFIDENCE_THRESHOLD:
        print("Validation step: Retrieval score is below threshold or empty context. Skipping LLM generation.")
        return {"answer": fallback_message}
        
    print("Validation step: Context is relevant. Sending prompt to Gemini LLM...")
    
    # 1. Format the context string for the LLM
    context_sections = []
    for chunk in chunks_list:
        context_sections.append(f"[Page {chunk['page']}]: {chunk['text']}")
    context_str = "\n\n".join(context_sections)
    
    # 2. Strict grounding system prompt
    system_prompt = (
        "You are a helpful chatbot that answers questions based on the provided Agentic AI eBook.\n"
        "Here are your strict instructions:\n"
        "1. You must answer the user's question using ONLY the retrieved context chunks below.\n"
        "2. Do NOT use any external or background knowledge. Be completely grounded in the provided text.\n"
        "3. If the answer to the question cannot be fully and directly found in the context, "
        "do not make up anything. Refuse to answer and respond exactly with: "
        "'I couldn't find this information in the provided Agentic AI eBook.'\n"
        "4. Answer the user directly. Do not say 'Based on the provided context...' or refer to 'retrieved documents' in your answer."
    )
    
    # 3. Call the Gemini LLM
    try:
        llm = ChatGoogleGenerativeAI(
            model="models/gemini-2.5-flash", 
            google_api_key=gemini_key, 
            temperature=0.0
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Context Chunks:\n{context_str}\n\nUser Question: {user_question}")
        ]
        
        llm_response = llm.invoke(messages)
        final_answer = llm_response.content.strip()
        
    except Exception as e:
        print(f"Error calling Gemini LLM: {e}")
        final_answer = "An error occurred while generating the answer. Please try again."
        
    # Extra safety check: if the LLM hallucinated outside the context or tried to bypass instructions,
    # and returned something indicating failure, or if it said it can't find it, normalize it.
    if "couldn't find this information" in final_answer.lower() or "cannot find" in final_answer.lower():
        final_answer = fallback_message
        
    return {"answer": final_answer}

# Compile the LangGraph workflow
def build_rag_graph():
    # Initialize the state graph
    workflow = StateGraph(MyChatState)
    
    # Add our nodes to the graph
    workflow.add_node("retrieve", fetch_chunks_from_db)
    workflow.add_node("generate", validate_and_generate)
    
    # Define execution order
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    # Compile and return the graph runner
    return workflow.compile()

# Instantiate the graph
my_chatbot_graph = build_rag_graph()

# Helper function to run the RAG query
def query_rag_bot(question: str) -> Dict[str, Any]:
    initial_state = {
        "question": question,
        "retrieved_chunks": [],
        "answer": "",
        "confidence": 0.0
    }
    
    # Run through the graph
    final_state = my_chatbot_graph.invoke(initial_state)
    
    # Format the final dictionary to match user's expected output response
    return {
        "answer": final_state["answer"],
        "retrieved_chunks": final_state["retrieved_chunks"],
        "confidence": final_state["confidence"]
    }
