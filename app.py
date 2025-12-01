# app.py — STREAMLIT VERSION (run in Colab or locally)
import streamlit as st
import requests
import json
import time

# === CONFIG — ONLY CHANGE THESE IF YOU USE DIFFERENT AUTH / MODEL ===
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
MODEL_NAME = "gemma3"   # or "gemma3:27b", "gemma3:9b", etc.

# Auto-detect ngrok URL from the running tunnel in the same session
try:
    import json, os
    ngrok_tunnels = json.load(open("/root/.config/ngrok/ngrok.yml"))["tunnels"]
    public_url = [t["public_url"] for t in ngrok_tunnels if "http" in t["proto"]][0]
    OLLAMA_URL = f"{public_url}/api/chat"
    st.success(f"Connected to gemma3 @ {public_url.split('//')[1]}")
except:
    # Fallback — paste manually if auto-detect fails
    OLLAMA_URL = st.text_input("ngrok URL (e.g. https://abc123.ngrok-free.dev)", 
                               value="https://ona-overcritical-extrinsically.ngrok-free.dev")
    OLLAMA_URL = f"{OLLAMA_URL}/api/chat"

# === Streamlit UI ===
st.set_page_config(page_title="gemma3 · Colab Live", layout="centered")
st.markdown("""
<style>
    .main {background-color: #0d1117; color: #c9d1d9;}
    .stChatMessage {background-color: #161b22; border-radius: 12px; padding: 12px; margin: 8px 0;}
    .stTextInput > div > div > input {background-color: #21262d; color: white; border-radius: 20px;}
    .stButton > button {background: #238636; color: white; border-radius: 20px; border: none;}
    .error {background: #5a1e2a; color: #ffa7a7; padding: 12px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.title("gemma3 · Live from Colab")
st.caption("Powered by Ollama + ngrok · Full conversation history")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm gemma3 running in Google Colab. Ask me anything!"}]

# Display chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User input
if prompt := st.chat_input("Type your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            payload = {
                "model": MODEL_NAME,
                "messages": st.session_state.messages,
                "stream": False
            }
            with requests.post(
                OLLAMA_URL,
                json=payload,
                auth=(USERNAME, PASSWORD),
                timeout=300,
                verify=False,
                stream=False
            ) as r:
                r.raise_for_status()
                response = r.json()
                reply = response.get("message", {}).get("content", "").strip()

                if not reply:
                    reply = "No response from model (empty reply)"

                full_response = reply
                message_placeholder.write(full_response)

        except requests.exceptions.ConnectionError:
            full_response = "Cannot connect – your ngrok tunnel is down or wrong URL"
            message_placeholder.error(full_response)
        except requests.exceptions.Timeout:
            full_response = "Timeout (5 min) – gemma3 is thinking too hard or frozen"
            message_placeholder.error(full_response)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                full_response = "Wrong username/password (401)"
            elif e.response.status_code == 404:
                full_response = "Model not found – did you pull gemma3?"
            else:
                full_response = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            message_placeholder.error(full_response)
        except Exception as e:
            full_response = f"Unexpected error: {str(e)}"
            message_placeholder.error(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})
