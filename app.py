# app.py — STREAMLIT + REAL-TIME STREAMING FROM GEMMA3 (Kaggle + ngrok)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

# UPDATE THIS EVERY TIME YOU RESTART KAGGLE
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"  # PASTE LATEST HERE

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
MODEL_NAME = "gemma3"

st.set_page_config(page_title="gemma3 · Live", layout="centered")

st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    section[data-testid="stSidebar"] {background: #161b22;}
    .stTextInput > div > div > input {background: #21262d; color: white; border-radius: 20px; border: 1px solid #30363d;}
    .stButton > button {background: #238636; color: white; border-radius: 20px; height: 50px; font-weight: bold;}
    .error {background: #5a1e2a; color: #ffa7a7; padding: 16px; border-radius: 12px; font-family: monospace;}
    .footer {text-align: center; color: #8b949e; font-size: 0.8em; margin-top: 50px;}
</style>
""", unsafe_allow_html=True)

st.title("gemma3 · Live from Kaggle")
st.caption("Streaming responses letter-by-letter · Ollama + ngrok")

with st.sidebar:
    st.header("Backend")
    st.code(NGROK_URL, language=None)
    st.caption(f"Model: `{MODEL_NAME}`")
    st.success("Connected")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "gemma3 is ready! I'm streaming live from Kaggle. Ask me anything!"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            payload = {
                "model": MODEL_NAME,
                "messages": st.session_state.messages,
                "stream": True   # This enables streaming
            }

            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=300,
                stream=True,
                verify=False
            ) as r:
                r.raise_for_status()

                for line in r.iter_lines():
                    if line:
                        try:
                            chunk = line.decode("utf-8")
                            if chunk.strip() == "data: [DONE]":
                                break
                            data = requests.utils.json.loads(chunk.replace("data: ", ""))
                            content = data.get("message", {}).get("content", "")
                            full_response += content
                            placeholder.write(full_response + "▌")  # blinking cursor effect
                        except:
                            continue

            # Final write without cursor
            placeholder.write(full_response or "No response received.")

        except requests.exceptions.ConnectionError:
            placeholder.error("Connection lost — Kaggle session or ngrok tunnel died.")
        except requests.exceptions.Timeout:
            placeholder.error("Timeout — gemma3 took too long.")
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 502:
                placeholder.error("502 Bad Gateway — Ollama crashed on Kaggle side.")
            else:
                placeholder.error(f"HTTP {e.response.status_code if e.response else 'Error'}")
        except Exception as e:
            placeholder.error(f"Error: {str(e)}")

        st.session_state.messages.append({"role": "assistant", "content": full_response})

st.markdown('<div class="footer">gemma3 · Kaggle + ngrok + Streamlit Streaming · 2025</div>', unsafe_allow_html=True)
