import os
import json
from datetime import datetime

LOG_FILE = "chat_history_logs.json"

def save_chat_log(question: str, answer: str, confidence: float):
    """
    Saves the user question, bot answer, confidence score, and timestamp to a local JSON file.
    This is wrapped in a try-except block so it NEVER crashes the main application if something goes wrong.
    """
    try:
        # 1. Create a log entry
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "answer": answer,
            "confidence_score": confidence
        }

        # 2. Read existing logs if file exists
        logs = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except Exception:
                logs = []

        # 3. Append and write back
        logs.append(log_entry)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4, ensure_ascii=False)
            
        print(f"[Logger] Saved query log to {LOG_FILE}")
    except Exception as e:
        # Silent failure to ensure main chatbot flow is never interrupted
        print(f"[Logger Warning] Failed to save chat log: {e}")
