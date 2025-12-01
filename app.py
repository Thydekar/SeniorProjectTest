# app.py
from flask import Flask, render_template, request, jsonify
import requests
import json

# ============ CONFIGURATION ============
OLLAMA_IP = "192.168.1.100"        # <<<<< CHANGE THIS TO YOUR OLLAMA SERVER IP
OLLAMA_PORT = 11434                # Default Ollama port (change if you modified it)
MODEL_NAME = "llama3.2"            # <<<<< CHANGE THIS TO YOUR DESIRED MODEL (e.g. "gemma2:2b", "phi3", etc.)
# =======================================

OLLAMA_URL = f"http://{OLLAMA_IP}:{OLLAMA_PORT}/api/chat"

app = Flask(__name__)

# Simple in-memory chat history (for a single user session)
chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Add user message to history
    chat_history.append({"role": "user", "content": user_message})

    try:
        # Prepare payload for Ollama /api/chat (streaming disabled for simplicity)
        payload = {
            "model": MODEL_NAME,
            "messages": chat_history,
            "stream": False
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=120)

        if response.status_code != 200:
            return jsonify({"error": f"Ollama error: {response.status_code} {response.text}"}), 500

        ollama_response = response.json()
        assistant_message = ollama_response.get("message", {}).get("content", "No response")

        # Add assistant reply to history
        chat_history.append({"role": "assistant", "content": assistant_message})

        return jsonify({"reply": assistant_message})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Cannot connect to Ollama at {OLLAMA_URL}: {str(e)}"}), 500

if __name__ == "__main__":
    print(f"Starting Flask web app...")
    print(f"Connecting to Ollama at {OLLAMA_URL}")
    print(f"Using model: {MODEL_NAME}")
    app.run(host="0.0.0.0", port=5000, debug=False)
