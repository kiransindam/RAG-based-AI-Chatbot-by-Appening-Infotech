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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import query_rag_bot
from logger_util import save_chat_log

# Create the FastAPI app
app = FastAPI(
    title="Agentic AI eBook Chatbot API",
    description="A simple RAG API using LangGraph, Pinecone, and Gemini API to answer questions strictly from the Agentic AI eBook."
)

# Enable CORS so our React frontend can connect to this backend from another port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this. For local development, "*" is fine.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request schema
class ChatRequest(BaseModel):
    question: str

# Define response schema matching the user's expected format
class ChatResponse(BaseModel):
    answer: str
    retrieved_chunks: list
    confidence: float

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Welcome to the Agentic AI eBook Chatbot API! Send a POST request to /chat to ask questions."
    }

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    user_query = payload.question.strip()
    
    if not user_query:
        raise HTTPException(status_code=400, detail="Question cannot be empty!")
        
    try:
        # Run the RAG query through our LangGraph pipeline
        result = query_rag_bot(user_query)
        # Log the query and response
        save_chat_log(user_query, result["answer"], result["confidence"])
        return result
    except Exception as e:
        print(f"Error handling /chat request: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal Server Error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Run server on port 8000
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
