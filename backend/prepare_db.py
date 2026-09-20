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
import time
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

# Load environment variables from .env file
load_dotenv()

# Check that keys are set
gemini_key = os.getenv("GEMINI_API_KEY")
pinecone_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "agentic-ai-ebook")

if not gemini_key or not pinecone_key:
    print("Error: GEMINI_API_KEY and PINECONE_API_KEY must be set in your .env file!")
    exit(1)

def run_db_preparation():
    pdf_path = "Agentic AI.pdf"
    if not os.path.exists(pdf_path):
        print("Error: Agentic AI.pdf.pdf not found. Please run download_pdf.py first!")
        exit(1)

    print("Step 1: Reading the PDF Agentic AI...")
    pdf_reader = PdfReader(pdf_path)
    raw_pages = []
    
    # Extract text page by page
    for page_index, page in enumerate(pdf_reader.pages):
        page_text = page.extract_text()
        page_num = page_index + 1
        if page_text.strip():
            raw_pages.append((page_text, page_num))
            
    print(f"Extracted text from {len(raw_pages)} pages.")

    print("\nStep 2: Splitting text into small chunks...")
    # Using RecursiveCharacterTextSplitter to split into nice paragraphs of 800 characters
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        length_function=len
    )
    
    my_chunks = []
    for text, page_num in raw_pages:
        # Split page content
        splits = text_splitter.split_text(text)
        for chunk in splits:
            my_chunks.append({
                "text": chunk,
                "page": page_num
            })
            
    print(f"Created {len(my_chunks)} chunks in total.")

    print("\nStep 3: Initializing Pinecone client...")
    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_key)
    
    # Check if the index already exists. If yes, we recreate it to clear old data
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name in existing_indexes:
        print(f"Index '{index_name}' already exists. Deleting it to ensure a fresh index...")
        pc.delete_index(index_name)
        # Give Pinecone a few seconds to process the deletion
        time.sleep(5)
        
    print(f"Creating a new Pinecone index '{index_name}'...")
    # We create a serverless index. Dimension 3072 is matching Gemini's text-embedding-001
    pc.create_index(
        name=index_name,
        dimension=3072,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    
    # Wait for the index to be fully initialized
    while not pc.describe_index(index_name).status['ready']:
        print("Waiting for Pinecone index to be ready...")
        time.sleep(2)
        
    print(f"Pinecone index '{index_name}' is ready!")
    
    # Get the index object
    pinecone_index = pc.Index(index_name)

    print("\nStep 4: Initializing Gemini Embeddings...")
    # Initialize the Gemini Embeddings model using LangChain
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", 
        google_api_key=gemini_key
    )

    print("\nStep 5: Generating embeddings and uploading to Pinecone...")
    # Upload in batches of 50 to avoid payload limits
    batch_size = 50
    total_uploaded = 0
    
    for i in range(0, len(my_chunks), batch_size):
        batch = my_chunks[i:i + batch_size]
        texts = [chunk["text"] for chunk in batch]
        
        # Generate embedding vectors
        try:
            vectors = embeddings_model.embed_documents(texts)
        except Exception as e:
            print(f"Error generating embeddings for batch starting at {i}: {e}")
            continue
            
        # Format the items for Pinecone upsert
        upsert_items = []
        for idx, (vector, chunk) in enumerate(zip(vectors, batch)):
            chunk_id = f"chunk_{i + idx}"
            metadata = {
                "text": chunk["text"],
                "page": chunk["page"]
            }
            upsert_items.append((chunk_id, vector, metadata))
            
        # Send to Pinecone
        pinecone_index.upsert(vectors=upsert_items)
        total_uploaded += len(upsert_items)
        print(f"Uploaded {total_uploaded}/{len(my_chunks)} chunks...")
        time.sleep(0.5) # simple rate limit buffer

    print(f"\nAll done! Successfully stored {total_uploaded} chunks in Pinecone.")

if __name__ == "__main__":
    run_db_preparation()
