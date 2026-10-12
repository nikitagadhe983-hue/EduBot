
import os
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv


# ---------------- CONFIGURATION ----------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

DATABASE = BASE_DIR / "edubot.db"

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
).rstrip("/")

MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_INSTRUCTIONS = """
You are EduBot, a friendly AI assistant for students.

- Explain topics in simple English.
- Teach programming step by step with examples.
- Provide exam notes and practice questions when requested.
- Explain difficult concepts in beginner-friendly language.
- Be respectful and honest when you are unsure.
"""


# ---------------- DATABASE ----------------

def get_connection():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation
            ON messages(conversation_id, id)
        """)


def save_message(conversation_id, role, content):
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO messages
                (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, role, content, timestamp))


def get_recent_messages(conversation_id, limit=12):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (conversation_id, limit)).fetchall()

    return [
        {"role": row["role"], "content": row["content"]}
        for row in reversed(rows)
    ]


initialize_database()


# ---------------- WEB PAGE ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- AI CHAT API ----------------

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}

    message = data.get("message", "")
    conversation_id = data.get("conversation_id", "")

    if not isinstance(message, str):
        return jsonify({"error": "Message must be text."}), 400

    if not isinstance(conversation_id, str):
        return jsonify({"error": "Invalid conversation ID."}), 400

    message = message.strip()

    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    if len(message) > 4000:
        return jsonify({
            "error": "Please keep messages under 4000 characters."
        }), 400

    try:
        conversation_id = str(uuid.UUID(conversation_id))
    except (ValueError, AttributeError, TypeError):
        return jsonify({"error": "Invalid conversation ID."}), 400

    # Save the user's message and load conversation history.
    save_message(conversation_id, "user", message)
    history = get_recent_messages(conversation_id)

    # Prepare messages for Ollama.
    messages = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTIONS
        }
    ]
    messages.extend(history)

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()

        result = response.json()
        answer = result.get("message", {}).get("content", "").strip()

        if not answer:
            app.logger.error("Ollama returned an empty response.")
            return jsonify({
                "error": "The AI returned an empty response."
            }), 502

        # Save the assistant's response.
        save_message(conversation_id, "assistant", answer)

        return jsonify({
            "answer": answer,
            "conversation_id": conversation_id
        })

    except requests.exceptions.Timeout:
        app.logger.exception("Ollama request timed out")
        return jsonify({
            "error": "The AI took too long to respond. Please try again."
        }), 504

    except requests.exceptions.ConnectionError:
        app.logger.exception("Could not connect to Ollama")
        return jsonify({
            "error": (
                "Cannot connect to Ollama. Make sure Ollama is running "
                "and the model is installed."
            )
        }), 503

    except requests.exceptions.HTTPError:
        app.logger.exception("Ollama returned an HTTP error")
        return jsonify({
            "error": (
                "Ollama could not process the request. "
                "Check the model name and server terminal."
            )
        }), 502

    except (ValueError, KeyError):
        app.logger.exception("Invalid response received from Ollama")
        return jsonify({
            "error": "Received an invalid response from the AI model."
        }), 502

    except Exception:
        app.logger.exception("Unexpected AI request failure")
        return jsonify({
            "error": "An unexpected error occurred. Check the Flask terminal."
        }), 500


# ---------------- CHAT HISTORY API ----------------

@app.route("/api/history/<conversation_id>", methods=["GET"])
def history(conversation_id):
    try:
        conversation_id = str(uuid.UUID(conversation_id))
    except (ValueError, AttributeError, TypeError):
        return jsonify({"error": "Invalid conversation ID."}), 400

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,)).fetchall()

    return jsonify({
        "messages": [dict(row) for row in rows]
    })


if __name__ == "__main__":
    app.run(debug=True)
