# Agentic AI eBook RAG Chatbot

This project is a Retrieval-Augmented Generation (RAG) Chatbot that answers queries exclusively based on the **"Agentic AI" eBook** (https://konverge.ai/pdf/Ebook-Agentic-AI.pdf).

Below is the documentation structured according to the assignment requirements.

---

## 1. README with Setup Instructions

### Prerequisites
- Python 3.10 or higher
- Node.js (v18 or higher) & npm
- A Pinecone account (Free tier is fine)
- A Google Gemini API key

### Directory Structure
```
AI Engineer Assignment/
├── backend/
│   ├── .env              # Loaded with your API keys
│   ├── requirements.txt  # Python requirements
│   ├── download_pdf.py   # Script to download ebook.pdf
│   ├── prepare_db.py     # Parses PDF, generates embeddings, uploads to Pinecone
│   ├── chatbot.py        # LangGraph workflow orchestration
│   ├── app.py            # FastAPI service exposing /chat
│   └── logger_util.py    # Log history saving helper
└── frontend/
    ├── src/
    │   ├── App.jsx       # Chatbot React UI
    │   ├── App.css       # Clean light theme layout styles
    │   └── index.css     # CSS variables and resets
    ├── index.html
    └── package.json      # React dependencies
```

### Installation Steps

#### Step 0: Clone the Repository
Open your terminal and run the following commands to clone the project and enter the directory:
```bash
git clone  
git clone https://github.com/kiransindam/RAG-based-AI-Chatbot-by-Appening-Infotech)
cd RAG-based-AI-Chatbot-by-Appening-Infotech)
```

#### Step A: Configure Environment Variables
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create a file named `.env` and configure your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_INDEX_NAME=agentic-ai-ebook
   ```

#### Step B: Set Up the Backend
1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   uv venv --python 3.12
   .\.venv\Scripts\Activate
   ```
3. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```
4. Download the source eBook:
   ```bash
   uv run download_pdf.py
   ```
5. Ingest the eBook pages into the Pinecone database:
   ```bash
   uv run prepare_db.py
   ```
6. Start the FastAPI server:
   ```bash
   uv run python -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```
   *(The server will start at `http://127.0.0.1:8000`)*

#### Step C: Set Up the Frontend
1. Open a new terminal and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install the Node packages:
   ```bash
   npm install
   ```
3. Launch the React dev server:
   ```bash
   npm run dev
   ```
4. Open the link displayed in the console (usually `http://localhost:5173`) in your browser.

---

## 2. Working RAG Chatbot (API & UI)

### Backend API Details
The backend is built with FastAPI. It exposes a `POST /chat` endpoint.
- **Endpoint**: `http://127.0.0.1:8000/chat`
- **Request Format (JSON)**:
  ```json
  {
    "question": "What is Agentic AI?"
  }
  ```
- **Response Format (JSON)**:
  ```json
  {
    "answer": "Agentic AI represents a shift from static tools to dynamic, autonomous systems...",
    "retrieved_chunks": [
      {
        "text": "Agentic AI refers to...",
        "page": 3,
        "score": 0.796
      }
    ],
    "confidence": 0.796
  }
  ```

### React Frontend UI Details
The frontend is a clean, single-page application built with React:
- **Clean Humanized Colors**: Avoids dark cyberpunk neon styles. Uses a clean light theme (warm slate gray background, dark text, and royal blue accents).
- **Collapsible Sources**: Clicking on "View Retrieved Source Chunks" expands an accordion showing the exact matching texts, page numbers, and cosine similarity scores.
- **Dynamic Confidence Badges**: Displays a color-coded status badge showing the average similarity score (Green for High, Orange for Medium, Red for Low).

---

## 3. Sample Queries (5–6)

The following queries are pre-configured as click-to-run buttons in the frontend sidebar:

1. **"What is Agentic AI?"**
   - *Expected Behavior*: Returns a detailed explanation of Agentic AI. High confidence score.
2. **"What are the core capabilities of an agent?"**
   - *Expected Behavior*: Returns a summary of agent capabilities from the eBook.
3. **"Explain single-agent vs multi-agent systems."**
   - *Expected Behavior*: Contrasts single and collaborative agents based on eBook sections.
4. **"What is the role of memory in AI agents?"**
   - *Expected Behavior*: Summarizes the function of long-term memory in agents.
5. **"What are the common challenges in building agents?"**
   - *Expected Behavior*: Summarizes security, feedback loops, and deployment challenges.
6. **"Who won the 2022 FIFA World Cup?"** *(Out-of-Scope Test)*
   - *Expected Behavior*: The similarity score falls below the validation threshold (`0.58`), and the chatbot bypasses the LLM to return the strict fallback: *"I couldn't find this information in the provided Agentic AI eBook."*

---

## 4. Short Architecture Explanation

```
[ User Input ]
      │
      ▼
[ LangGraph: Node 1 (Retrieve) ]
      │
      ├──► Convert query to vector with gemini-embedding-001
      ├──► Search Pinecone for top-4 closest matching text blocks
      └──► Calculate average similarity score (Confidence)
      │
      ▼
[ LangGraph: Node 2 (Validate & Generate) ]
      │
      ├───► [ YES ] ──► (Average Score < 0.58) ──► Skip LLM. Return fallback message:
      │                                            "I couldn't find this information..."
      │
      └───► [ NO  ] ──► (Average Score >= 0.58) ──► Send query + chunks to Gemini 2.5 Flash
                                                    with strict grounding system prompt.
```

### Key Orchestration Features:
- **LangGraph State Management**: Tracks query execution states (`question`, `retrieved_chunks`, `answer`, `confidence`) inside a state graph workflow.
- **Strict Grounding Prompt**: Gemini is instructed with a zero-temperature parameter to prevent hallucinations and answer *only* from the context.
- **Workaround for Restricted DLL environments**: Includes a dynamic pure-Python mock for `xxhash` to prevent AppLocker/WDAC DLL loading failures on restricted Windows systems.
#
