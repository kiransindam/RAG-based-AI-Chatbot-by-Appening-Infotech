import { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [chatMessages, setChatMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isApiOnline, setIsApiOnline] = useState(false);
  
  const bottomScrollRef = useRef(null);

  // Sample queries from the eBook (plus a couple to test grounding validation)
  const sampleQuestions = [
    "What is Agentic AI?",
    "What are the core capabilities of an agent?",
    "Explain single-agent vs multi-agent systems.",
    "What is the role of memory in AI agents?",
    "What are the common challenges in building agents?",
    "Who won the 2022 FIFA World Cup?" // Outside-knowledge query to test grounding fallback!
  ];

  // Check if backend API is online when the component mounts
  useEffect(() => {
    fetch('http://localhost:8000/')
      .then((res) => {
        if (res.ok) setIsApiOnline(true);
      })
      .catch((err) => {
        console.error("API offline:", err);
        setIsApiOnline(false);
      });
  }, []);

  // Auto-scroll to the bottom of the chat when new messages arrive
  useEffect(() => {
    bottomScrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isSearching]);

  // Send a question to the FastAPI server
  const sendQuery = async (questionText) => {
    if (!questionText.trim() || isSearching) return;

    // 1. Add user's question to the chat list
    const newUserMessage = {
      sender: 'user',
      text: questionText
    };
    
    setChatMessages((prev) => [...prev, newUserMessage]);
    setUserInput('');
    setIsSearching(true);

    // 2. Fetch answer from the backend API
    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: questionText }),
      });

      if (!response.ok) {
        throw new Error(`Server returned error: ${response.status}`);
      }

      const data = await response.json();
      
      // 3. Add bot's answer and metadata to the chat list
      const newBotMessage = {
        sender: 'bot',
        text: data.answer,
        retrieved_chunks: data.retrieved_chunks || [],
        confidence: data.confidence || 0.0
      };
      
      setChatMessages((prev) => [...prev, newBotMessage]);
    } catch (error) {
      console.error("Error communicating with chatbot API:", error);
      const errorBotMessage = {
        sender: 'bot',
        text: "I couldn't reach the backend server. Please make sure the FastAPI server is running on port 8000.",
        retrieved_chunks: [],
        confidence: 0.0
      };
      setChatMessages((prev) => [...prev, errorBotMessage]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    sendQuery(userInput);
  };

  // Helper to determine CSS class for confidence badge
  const getConfidenceClass = (score) => {
    if (score >= 0.6) return 'high';
    if (score >= 0.45) return 'medium';
    return 'low';
  };

  return (
    <div className="app-container">
      {/* Sidebar: App details, eBook link, and sample questions */}
      <aside className="sidebar">
        <div className="logo-section">
          <span className="logo-icon">📖</span>
          <div className="logo-text">
            <h1>Agentic AI Chat</h1>
            <p>E-Book Knowledge Base</p>
          </div>
        </div>

        <div className="info-box">
          <h3>Knowledge Source</h3>
          <p>
            This assistant answers questions strictly based on the eBook <strong>"Agentic AI: The Next Frontier"</strong>.
          </p>
          <a 
            href="https://konverge.ai/pdf/Ebook-Agentic-AI.pdf" 
            target="_blank" 
            rel="noopener noreferrer"
            className="ebook-link"
          >
            Open Original PDF ↗
          </a>
        </div>

        <div className="sample-queries-section">
          <h3>Sample Queries</h3>
          {sampleQuestions.map((q, idx) => (
            <button 
              key={idx}
              className="sample-query-btn"
              onClick={() => sendQuery(q)}
              disabled={isSearching}
            >
              {q}
            </button>
          ))}
        </div>
      </aside>

      {/* Main Chat Panel */}
      <main className="chat-area">
        {/* Header */}
        <header className="chat-header">
          <div className="header-title">
            <h2>RAG Assistant (LangGraph + Pinecone)</h2>
          </div>
          <div className="connection-badge">
            <span className={`connection-dot ${isApiOnline ? '' : 'offline'}`} />
            {isApiOnline ? "API Connected" : "API Offline"}
          </div>
        </header>

        {/* Message History list */}
        <div className="messages-container">
          {chatMessages.length === 0 ? (
            <div className="welcome-container">
              <span className="welcome-icon">🤖</span>
              <h2>Hello! Ask me about Agentic AI.</h2>
              <p>
                I am a RAG-based AI agent. Type a question or click one of the sample queries in the left panel to begin. I will only answer using facts from the eBook.
              </p>
            </div>
          ) : (
            chatMessages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender}`}>
                <span className="message-label">
                  {msg.sender === 'user' ? 'You' : 'Assistant'}
                </span>
                
                <div className="message-bubble">
                  {msg.text}
                  
                  {/* Display metadata for chatbot responses */}
                  {msg.sender === 'bot' && msg.retrieved_chunks && msg.retrieved_chunks.length > 0 && (
                    <div className="response-metadata">
                      {/* Confidence Score row */}
                      <div className="confidence-row">
                        <span className="confidence-label">Confidence Score:</span>
                        <span className={`confidence-badge ${getConfidenceClass(msg.confidence)}`}>
                          {msg.confidence.toFixed(3)}
                        </span>
                      </div>
                      
                      {/* Collapsible Accordion for Sources */}
                      <details className="chunks-accordion">
                        <summary className="accordion-summary">
                          View Retrieved Source Chunks ({msg.retrieved_chunks.length})
                        </summary>
                        <div className="chunks-list">
                          {msg.retrieved_chunks.map((chunk, cIdx) => (
                            <div key={cIdx} className="chunk-item">
                              <div className="chunk-header">
                                <span className="chunk-page">Page {chunk.page}</span>
                                <span className="chunk-score">Score: {chunk.score.toFixed(3)}</span>
                              </div>
                              <div className="chunk-text">"{chunk.text}"</div>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          
          {/* Typing thinking indicator */}
          {isSearching && (
            <div className="message bot">
              <span className="message-label">Assistant</span>
              <div className="message-bubble">
                <div className="typing-indicator">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomScrollRef} />
        </div>

        {/* Input Bar Form */}
        <div className="chat-input-container">
          <form className="input-form" onSubmit={handleFormSubmit}>
            <input 
              type="text" 
              className="chat-input"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="Ask a question about the eBook (e.g. What is memory?)..."
              disabled={isSearching}
            />
            <button 
              type="submit" 
              className="send-btn"
              disabled={isSearching || !userInput.trim()}
            >
              Send
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

export default App;
