# app.py – works RIGHT NOW with your current ngrok tunnel + gemma3
from flask import Flask, request, jsonify, render_template_string
import requests

# ============ YOUR CURRENT LIVE CONFIG (from the screenshot) ============
NGROK_BASE      = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_BASE}/api/chat"      # correct chat endpoint
MODEL_NAME      = "gemma3"                      # change only if you pulled a different tag

# Basic Auth required by this tunnel
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
# =====================================================================

app = Flask(__name__)
chat_history = []  # one continuous conversation

HTML = """
<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gemma3 × ngrok chat</title>
<style>
    body{margin:0;background:#0d1117;height:100vh;display:flex;justify-content:center;font-family:system-ui;}
    #box{max-width:900px;width:100%;background:#161b22;display:flex;flex-direction:column;height:100vh;}
    #msgs{flex:1;overflow-y:auto;padding:20px;color:#c9d1d9;}
    .msg{max-width:80%;margin:10px 0;padding:14px 20px;border-radius:18px;line-height:1.5;word-wrap:break-word;}
    .user{background:#2f81f7;color:white;margin-left:auto;border-bottom-right-radius:4px;}
    .assistant{background:#30363d;color:#c9d1d9;border-bottom-left-radius:4px;}
    #in{padding:15px;display:flex;gap:12px;background:#0d1117;border-top:1px solid #30363d;}
    input{flex:1;padding:14px 20px;background:#0d1117;border:1px solid #30363d;border-radius:30px;color:white;font-size:16px;}
    button{padding:0 30px;background:#238636;color:white;border:none;border-radius:30px;cursor:pointer;font-weight:600;}
    button:hover{background:#2ea043;}
</style>
</head><body>
<div id="box">
    <div id="msgs"></div>
    <div id="in">
        <input type="text" id="i" placeholder="Ask gemma3..." autocomplete="off">
        <button onclick="send()">Send</button>
    </div>
</div>
<script>
    const m=document.getElementById("msgs"), i=document.getElementById("i"); i.focus();
    function add(t,w){const d=document.createElement("div"); d.className="msg "+w; d.textContent=t; m.appendChild(d); m.scrollTop=m.scrollHeight;}
    async function send(){
        const msg=i.value.trim(); if(!msg)return;
        add(msg,"user"); i.value="";
        const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({msg})});
        const j=await r.json();
        add(j.reply||"Error: "+(j.error||"unknown"),"assistant");
    }
    i.addEventListener("keypress",e=>{if(e.key==="Enter")send();});
    add("gemma3 is online and ready! (via your current ngrok tunnel)","assistant");
</script>
</body></html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("msg", "").strip()
    if not msg:
        return jsonify({"error": "empty"}), 400

    chat_history.append({"role": "user", "content": msg})

    try:
        payload = {
            "model": MODEL_NAME,
            "messages": chat_history,
            "stream": False
        }
        r = requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            auth=(USERNAME, PASSWORD),
            timeout=300
        )
        r.raise_for_status()
        reply = r.json()["message"]["content"]
        chat_history.append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\nWeb chat → http://127.0.0.1:5000")
    print(f"Model     → {MODEL_NAME}")
    print(f"Ollama    → {OLLAMA_CHAT_URL}\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
