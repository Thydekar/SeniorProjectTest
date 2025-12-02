# app.py — PASTE YOUR KAGGLE NGROK URL BELOW (no secrets needed)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

# PASTE YOUR LATEST NGROK URL HERE EVERY TIME YOU RESTART KAGGLE
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"  # CHANGE THIS

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
MODEL_NAME = "gemma3"

st.set_page_config(page_title="gemma3 · Kaggle Live", layout="centered")

st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    .stChatMessage {margin: 10px 0;}
    section[data-testid="stSidebar"] {background: #161b22;}
    .stTextInput > div > div > input {background: #21262d; color: white; border-radius: 20px; border: 1px solid #30363d;}
    .stButton > button {background: #238636; color: white; border-radius: 20px; height: 50px; font-weight: bold;}
    .error {background: #5a1e2a; color: #ffa7a7; padding: 16px; border-radius: 12px; font-family: monospace;}
    .footer {text-align: center; color: #8b949e; font-size: 0.8em; margin-top: 50px;}
</style>
""", unsafe_allow_html=True)

st.title("gemma3 · Live from Kaggle")
st.caption("Ollama + ngrok + Streamlit · Full chat history · Powered by Google Gemma 3")

with st.sidebar:
    st.header("Backend")
    st.code(NGROK_URL, language=None)
    st.caption(f"Model: `{MODEL_NAME}`")
    st.success("Connected") if NGROK_URL else st.error("No URL set")
    st.markdown("---")
    st.markdown("**How to update:**")
    st.markdown("1. Run Kaggle notebook\n2. Copy new ngrok URL\n3. Paste it above\n4. Save + redeploy")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "gemma3 is online! Ask me anything. Running live from Kaggle via ngrok."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Send a message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            payload = {
                "model": MODEL_NAME,
                "messages": st.session_state.messages,
                "stream": False
            }
            r = requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=300,
                verify=False
            )
            r.raise_for_status()
            reply = r.json()["message"]["content"].strip()
            placeholder.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

        except requests.exceptions.ConnectionError:
            error = "Connection failed — ngrok tunnel is down or Kaggle session died"
            placeholder.error(error)
        except requests.exceptions.Timeout:
            error = "Timeout (5 min) — gemma3 is slow or frozen"
            placeholder.error(error)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 502:
                error = "502 Bad Gateway — Ollama crashed or port not open"
            elif e.response.status_code == 401:
                error = "401 Unauthorized — wrong auth"
            else:
                error = f"HTTP {e.response.status_code} — {e.response.text[:200]}"
            placeholder.error(error)
        except Exception as e:
            placeholder.error(f"Error: {str(e)}")

st.markdown('<div class="footer">gemma3 · Kaggle + ngrok + Streamlit · 2025</div>', unsafe_allow_html=True)
