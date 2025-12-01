# app.py – Works 100% with your Colab ngrok tunnel + gemma3
from flask import Flask, request, jsonify, render_template_string
import requests
import time

# ==============================================================
# UPDATE THIS LINE ONLY WHEN YOU RUN THE COLAB NOTEBOOK
# ==============================================================
NGROK_BASE = "https://CHANGE-THIS-TO-YOUR-LATEST-NGROK-URL.ngrok-free.dev"  # ← Paste here from Colab!

OLLAMA_CHAT_URL = f"{NGROK_BASE}/api/chat"
MODEL_NAME = "gemma3"                    # or gemma3:27b / gemma3:9b if that's what you pulled

# Your ngrok Basic Auth credentials (same as in Colab)
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
# ==============================================================

app = Flask(__name__)
chat_history = []  # Continuous conversation

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>gemma3 • Live via ngrok</title>
    <style>
        body {margin:0;background:#0d1117;height:100vh;display:flex;justify-content:center;font-family:system-ui;color:#c9d1d9;}
        #box {max-width:900px;width:100%;background:#161b22;display:flex;flex-direction:column;height:100vh;box-shadow:0 0 30px rgba(0,0,0,0.5);}
        #msgs {flex:1;overflow-y:auto;padding:20px;}
        .msg {max-width:80%;margin:10px 0;padding:14px 20px;border-radius:18px;line-height:1.5;word-wrap:break-word;}
        .user {background:#2f81f7;color:white;margin-left:auto;border-bottom-right-radius:4px;}
        .assistant {background:#30363d;color:#c9d1d9;border-bottom-left-radius:4px;}
        .error {background:#5a1e2a;color:#ffa7a7;padding:12px 16px;border-radius:12px;}
        #in {padding:15px;display:flex;gap:12px;background:#0d1117;border-top:1px solid #30363d;}
        input {flex:1;padding:14px 20px;background:#0d1117;border:1px solid #30363d;border-radius:30px;color:white;font-size:16px;}
        button {padding:0 32px;background:#238636;color:white;border:none;border-radius:30px;cursor:pointer;font-weight:600;}
        button:hover {background:#2ea043;}
        .header {padding:15px;text-align:center;background:#21262d;font-size:14px;}
    </style>
</head>
<body>
    <div class="header">gemma3 • Running live from Google Colab via ngrok</div>
    <div id="box">
        <div id="msgs"></div>
        <div id="in">
            <input type="text" id="i" placeholder="Ask gemma3 anything..." autocomplete="off">
            <button onclick="send()">Send</button>
        </div>
    </div>
    <script>
        const m = document.getElementById("msgs"), i = document.getElementById("i"); i.focus();
        function add(text, type) {
            const div = document.createElement("div");
            div.className = "msg " + type;
            div.textContent = text;
            m.appendChild(div);
            m.scrollTop = m.scrollHeight;
        }
        async function send() {
            const msg = i.value.trim();
            if (!msg) return;
            add(msg, "user");
            i.value = "";
            const resp = await fetch("/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({msg})
            });
            const data = await resp.json();
            if (data.reply) add(data.reply, "assistant");
            else add("ERROR → " + (data.error || "Unknown"), "error");
        }
        i.addEventListener("keypress", e => { if (e.key === "Enter") send(); });
        add("gemma3 is online and ready! 🚀 (via your Colab ngrok tunnel)", "assistant");
    </script>
</body>
</html>
"""

@app.route("/")
def index():
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

        start = time.time()
        r = requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            auth=(USERNAME, PASSWORD),
            timeout=300,
            verify=False   # Free ngrok sometimes has cert quirks
        )
        elapsed = round(time.time() - start, 1)

        if r.status_code != 200:
            error_msg = f"HTTP {r.status_code} – {r.text[:300]} (took {elapsed}s)"
            return jsonify({"error": error_msg})

        result = r.json()
        reply = result.get("message", {}).get("content", "").strip()
        if not reply:
            return jsonify({"error": f"Empty reply from model (took {elapsed}s)"})

        chat_history.append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Cannot reach Ollama – ngrok tunnel is down or wrong URL"})
    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout (300s) – gemma3 is thinking too long or frozen"})
    except requests.exceptions.SSLError:
        return jsonify({"error": "SSL error – restart ngrok in Colab (common on free tier)"})
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"})

if __name__ == "__main__":
    print("\n" + "="*60)
    print("GEMMA3 WEB CHAT STARTED")
    print("="*60)
    print(f"   Model        : {MODEL_NAME}")
    print(f"   Ollama URL   : {OLLAMA_CHAT_URL}")
    print(f"   Auth         : {USERNAME}:{'*'*len(PASSWORD)}")
    print(f"   Chat UI      : http://127.0.0.1:5000")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
