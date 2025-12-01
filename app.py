# app.py
from flask import Flask, request, jsonify, render_template_string
import requests

# ============ CONFIGURATION ============
OLLAMA_IP = "192.168.1.100"      # CHANGE THIS
OLLAMA_PORT = 11434
MODEL_NAME = "llama3.2"          # CHANGE THIS
# =======================================

OLLAMA_URL = f"http://{OLLAMA_IP}:{OLLAMA_PORT}/api/chat"

app = Flask(__name__)
chat_history = []

# Full HTML + CSS + JS directly in the Python file (no templates folder needed)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ollama Chat • {{ model }}</title>
    <style>
        body { font-family: system-ui, sans-serif; margin:0; background:#f0f2f5; height:100vh; display:flex; justify-content:center; }
        #chatbox { width:100%; max-width:900px; background:white; display:flex; flex-direction:column; height:100vh; box-shadow:0 0 20px rgba(0,0,0,0.1); }
        #messages { flex:1; overflow-y:auto; padding:20px; }
        .message { max-width:80%; margin:10px 0; padding:12px 18px; border-radius:20px; line-height:1.5; }
        .user { background:#007bff; color:white; align-self:flex-end; margin-left:auto; border-bottom-right-radius:4px; }
        .assistant { background:#e9ecef; color:#1c1e21; align-self:flex-start; border-bottom-left-radius:4px; }
        #input-area { padding:15px; background:#f8f9fa; border-top:1px solid #ddd; display:flex; gap:10px; }
        #user-input { flex:1; padding:14px 20px; border:1px solid #ccc; border-radius:30px; font-size:16px; }
        button { padding:0 24px; background:#007bff; color:white; border:none; border-radius:30px; cursor:pointer; font-size:16px; }
        button:hover { background:#0056b3; }
    </style>
</head>
<body>
    <div id="chatbox">
        <div id="messages"></div>
        <div id="input-area">
            <input type="text" id="user-input" placeholder="Type a message..." autocomplete="off">
            <button onclick="send()">Send</button>
        </div>
    </div>

    <script>
        const messages = document.getElementById("messages");
        const input = document.getElementById("user-input");
        input.focus();

        function add(msg, sender) {
            const div = document.createElement("div");
            div.className = "message " + sender;
            div.textContent = msg;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        async function send() {
            const text = input.value.trim();
            if (!text) return;
            add(text, "user");
            input.value = "";

            const resp = await fetch("/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({message: text})
            });
            const data = await resp.json();
            add(data.reply || "Error: " + (data.error || "Unknown"), "assistant");
        }

        input.addEventListener("keypress", e => { if (e.key === "Enter") send(); });
        add("Hello! I'm running {{ model }} via Ollama. Ask me anything!", "assistant");
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, model=MODEL_NAME)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    chat_history.append({"role": "user", "content": user_message})

    try:
        payload = {
            "model": MODEL_NAME,
            "messages": chat_history,
            "stream": False
        }
        r = requests.post(OLLAMA_URL, json=payload, timeout=300)
        r.raise_for_status()
        reply = r.json()["message"]["content"]
        chat_history.append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"Ollama Chat UI → http://localhost:5000")
    print(f"Connected to Ollama at {OLLAMA_URL} using model '{MODEL_NAME}'")
    app.run(host="0.0.0.0", port=5000, debug=False)
