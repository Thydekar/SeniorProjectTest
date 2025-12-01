# app.py — FINAL WORKING VERSION (Dec 2025)
from flask import Flask, request, jsonify, render_template_string
import requests

# UPDATE ONLY THIS LINE FROM YOUR COLAB OUTPUT
NGROK_BASE = "https://ona-overcritical-extrinsically.ngrok-free.dev"  # ← PASTE HERE

OLLAMA_CHAT_URL = f"{NGROK_BASE}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"

# Try these model names in order (most common gemma3 tags)
MODELS_TO_TRY = ["gemma3", "gemma3:27b", "gemma3:9b", "gemma3:latest"]

app = Flask(__name__)
chat_history = []

HTML = """
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gemma3 • Colab Live</title>
<style>
    body{margin:0;background:#0d1117;height:100vh;display:flex;flex-direction:column;font-family:system-ui;color:#c9d1d9;}
    #msgs{flex:1;overflow-y:auto;padding:20px;}
    .msg{max-width:80%;margin:10px 0;padding:14px 20px;border-radius:18px;line-height:1.5;word-wrap:break-word;}
    .user{background:#2f81f7;color:white;margin-left:auto;}
    .assistant{background:#30363d;color:#c9d1d9;}
    .error{background:#5a1e2a;color:#ff7b72;}
    #in{padding:15px;display:flex;gap:10px;background:#0d1117;border-top:1px solid #30363d;}
    input{flex:1;padding:14px 20px;background:#0d1117;border:1px solid #30363d;border-radius:30px;color:white;font-size:16px;}
    button{padding:0 30px;background:#238636;color:white;border:none;border-radius:30px;cursor:pointer;}
</style>
</head><body>
<div id="msgs"></div>
<div id="in">
    <input type="text" id="i" placeholder="Type a message..." autocomplete="off">
    <button onclick="send()">Send</button>
</div>
<script>
    const m=document.getElementById("msgs"), i=document.getElementById("i"); i.focus();
    function add(t,c){const d=document.createElement("div"); d.className="msg "+c; d.textContent=t; m.appendChild(d); m.scrollTop=m.scrollHeight;}
    async function send(){
        const msg=i.value.trim(); if(!msg)return;
        add(msg,"user"); i.value="";
        const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({msg})});
        const j=await r.json();
        add(j.reply || "ERROR: "+j.error, j.reply?"assistant":"error");
    }
    i.addEventListener("keypress",e=>{if(e.key==="Enter")send();});
    add("gemma3 loading...","assistant");
</script>
</body></html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("msg","").strip()
    if not user_msg:
        return jsonify({"error": "empty message"})

    chat_history.append({"role": "user", "content": user_msg})

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    for model in MODELS_TO_TRY:
        payload = {
            "model": model,
            "messages": chat_history,
            "stream": False
        }
        try:
            r = requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=(USERNAME, PASSWORD),
                headers=headers,
                timeout=180,
                verify=False   # required for free ngrok
            )
            if r.status_code == 200:
                reply = r.json().get("message", {}).get("content", "").strip()
                if reply:
                    chat_history.append({"role": "assistant", "content": reply})
                    return jsonify({"reply": reply})
            elif r.status_code == 404:
                continue  # try next model name
            else:
                return jsonify({"error": f"HTTP {r.status_code}: {r.text[:200]}"})
        except Exception as e:
            return jsonify({"error": f"Request failed: {str(e)}"})

    return jsonify({"error": "All model names failed — check ollama list in Colab"})

if __name__ == "__main__":
    print("gemma3 chat LIVE")
    print(f"URL: {OLLAMA_CHAT_URL}")
    app.run(host="0.0.0.0", port=5000)
