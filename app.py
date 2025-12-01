# app.py - Ollama + gemma3 via your ngrok tunnel with auth
from flask import Flask, request, jsonify, render_template_string
import requests

# ============ YOUR CONFIG (already set for you) ============
NGROK_BASE = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_BASE}/api/chat"      # correct streaming chat endpoint
MODEL_NAME = "gemma3"                           # or "gemma3:27b", "gemma3:9b", etc. - whatever you pulled

# ngrok requires Basic Auth
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"

# ===============================================================

app = Flask(__name__)
chat_history = []  # persistent conversation

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>gemma3 • ngrok chat</title>
    <style>
        body {font-family:system-ui;margin:0;background:#0d1117;height:100vh;display:flex;justify-content:center;}
        #box {width:100%;max-width:900px;background:#161b22;display:flex;flex-direction:column;height:100vh;}
        #msgs {flex:1;overflow-y:auto;padding:20px;color:#c9d1d9;}
        .msg {max-width:80%;margin:15px 0;padding:12px 18px;border-radius:18px;line-height:1.5;word-wrap:break-word;}
        .user {background:#2f81f7;color:white;align-self:flex-end;margin-left:auto;border-bottom-right-radius:4px;}
        .assistant {background:#30363d;color:#c9d1d9;align-self:flex-start;border-bottom-left-radius:4px;}
        #inputarea {padding:15px;display:flex;gap:10px;background:#0d1117;border-top:1px solid #30363d;}
        input {flex:1;padding:14px 20px;background:#0d1117;border:1px solid #30363d;border-radius:30px;color:white;font-size:16px;}
        button {padding:0 28px;background:#238636;color:white;border:none;border-radius:30px;cursor:pointer;font-weight:600;}
        button:hover {background:#2ea043;}
    </style>
</head>
<body>
    <div id="box">
        <div id="msgs"></div>
        <div id="inputarea">
            <input type="text" id="txt" placeholder="Ask gemma3 anything..." autocomplete="off">
            <button onclick="send()">Send</button>
        </div>
    </div>
    <script>
        const msgs = document.getElementById("msgs");
        const input = document.getElementById("txt");
        input.focus();
        function add(text, who) {
            const d = document.createElement("div");
            d.className = "msg " + who;
            d.textContent = text;
            msgs.appendChild(d);
            msgs.scrollTop = msgs.scrollHeight;
        }
        async function send() {
            const msg = input.value.trim();
            if (!msg) return;
            add(msg, "user");
            input.value = "";
            const resp = await fetch("/chat", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({msg})});
            const data = await resp.json();
            add(data.reply || "Error: "+(data.error||"???"), "assistant");
        }
        input.addEventListener("keypress", e=>{if(e.key==="Enter")send();});
        add("gemma3 is ready! (via your ngrok tunnel)", "assistant");
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("msg", "").strip()
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    chat_history.append({"role": "user", "content": user_msg})

    try:
        payload = {
            "model": MODEL_NAME,
            "messages": chat_history,
            "stream": False
        }
        auth = (USERNAME, PASSWORD)

        r = requests.post(OLLAMA_CHAT_URL, json=payload, auth=auth, timeout=300)
        r.raise_for_status()
        reply = r.json()["message"]["content"]

        chat_history.append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("gemma3 web chat started!")
    print(f"   Model : {MODEL_NAME}")
    print(f"   Ollama: {OLLAMA_CHAT_URL}")
    print("   Open → http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
