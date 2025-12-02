# app.py — gemma3 with REAL-TIME TOKEN STREAMING (typing effect)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time

# UPDATE THIS EVERY TIME YOU RESTART KAGGLE
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"  # ← CHANGE HERE

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
MODEL_NAME = "gemma3"

st.set_page_config(page_title="gemma3 · Live Typing", layout="centered")

st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    section[data-testid="stSidebar"] {background: #161b22;}
    .stTextInput > div > div > input {background: #21262d; color: white; border-radius: 20px; border: 1px solid #30363d;}
    .stButton > button {background: #238636; color: white; border-radius: 20px; height: 50px; font-weight: bold;}
    .error {background: #5a1e2a; color: #ffa7a7; padding: 16px; border-radius: 12px;}
    .footer {text-align: center; color: #8b949e; font-size: 0.8em; margin-top: 60px;}
    .typing {color: #58a6ff; font-style: italic;}
</style>
""", unsafe_allow_html=True)

st.title("gemma3 · Live from Kaggle")
st.caption("Streaming tokens in real time — just like ChatGPT")

with st.sidebar:
    st.header("Backend")
    st.code(NGROK_URL, language=None)
    st.caption(f"Model: `{MODEL_NAME}`")
    st.success("Connected")
    st.markdown("---")
    st.markdown("**To update:**\n1. Run Kaggle notebook\n2. Copy new ngrok URL\n3. Paste above\n4. Redeploy")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "gemma3 is ready and streaming live from Kaggle! Ask me anything."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            payload = {
                "model": MODEL_NAME,
                "messages": st.session_state.messages,
                "stream": True  # ← THIS ENABLES STREAMING
            }

            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600,
                verify=False,
                stream=True
            ) as r:
                r.raise_for_status()

                # Stream response token by token
                for line in r.iter_lines():
                    if line:
                        try:
                            json_chunk = json.loads(line.decode("utf-8"))
                            token = json_chunk.get("message", {}).get("content", "")
                            full_response += token
                            placeholder.markdown(full_response + "▊")  # blinking cursor
                            time.sleep(0.01)  # smooth typing speed
                        except:
                            continue  # skip malformed lines

                # Final clean response (remove cursor)
                placeholder.markdown(full_response)

        except requests.exceptions.ConnectionError:
            error = "Connection lost — Kaggle session or ngrok died"
            placeholder.error(error)
        except requests.exceptions.Timeout:
            error = "Timed out — gemma3 took too long"
            placeholder.error(error)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 502:
                error = "502 — Ollama crashed in Kaggle"
            elif e.response.status_code == 401:
                error = "401 — Wrong auth"
            else:
                error = f"HTTP {e.response.status_code}"
            placeholder.error(error)
        except Exception as e:
            placeholder.error(f"Error: {str(e)}")

        # Save final response
        if full_response:
            st.session_state.messages.append({"role": "assistant", "content": full_response})

st.markdown('<div class="footer">gemma3 · Kaggle + ngrok + Streamlit · Real-time streaming · 2025</div>', unsafe_allow_html=True)
