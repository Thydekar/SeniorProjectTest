# app.py — FOR GITHUB → STREAMLIT CLOUD (connects to Kaggle ngrok + gemma3)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

# ──────────────────────────────────────────────────────────────
# UPDATE THIS URL EVERY TIME YOU START A NEW KAGGLE NOTEBOOK
# ──────────────────────────────────────────────────────────────
NGROK_URL = st.secrets.get("NGROK_URL", "https://paste-your-latest-kaggle-ngrok-url-here.ngrok-free.dev")
# Example: https://a1b2c3d4-12-34-567-890.ngrok-free.dev

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"

# Your ngrok basic auth (same as in Kaggle notebook)
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"

# Model name — change only if you pulled a different tag
MODEL_NAME = "gemma3"
# ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="gemma3 · Kaggle Live", layout="centered", menu_items=None)

# Dark GitHub-style theme
st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    .stChatMessage {margin: 8px 0;}
    section[data-testid="stSidebar"] {background: #161b22;}
    .stTextInput > div > div > input {background: #21262d; color: white; border-radius: 16px;}
    .stButton > button {background: #238636; color: white; border-radius: 16px; border: none; height: 48px;}
    .error-box {background: #5a1e2a; color: #ffa7a7; padding: 12px; border-radius: 12px; font-family: monospace;}
    .footer {text-align: center; color: #8b949e; font-size: 0.8em; margin-top: 40px;}
</style>
""", unsafe_allow_html=True)

st.title("gemma3 · Live from Kaggle")
st.caption("Ollama + ngrok tunnel → full conversation history · powered by Google Gemma 3")

# Sidebar info
with st.sidebar:
    st.header("Backend")
    st.code(OLLAMA_CHAT_URL.split("/api")[0], language=None)
    st.caption(f"Model: `{MODEL_NAME}`")
    st.caption("Status: Connected" if NGROK_URL else "No URL configured")
    st.markdown("---")
    st.markdown("**Instructions**")
    st.markdown("1. Run your Kaggle notebook  \n2. Copy the new ngrok URL  \n3. Paste it in Streamlit secrets → `NGROK_URL`  \n4. Redeploy")

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "gemma3 is ready! Ask me anything. This instance is running live from a Kaggle notebook via ngrok."}
    ]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User input
if prompt := st.chat_input("Type your message here..."):
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

            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=300,
                verify=False
            ) as r:
                r.raise_for_status()
                data = r.json()
                reply = data.get("message", {}).get("content", "").strip()

                if not reply:
                    reply = "Empty response from model"

                placeholder.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

        except requests.exceptions.ConnectionError:
            error = "Cannot reach Kaggle – ngrok tunnel is down or wrong URL"
            placeholder.error(error)
            st.session_state.messages.append({"role": "assistant", "content": error})
        except requests.exceptions.Timeout:
            error = "Timeout (5 min) – gemma3 is slow or frozen"
            placeholder.error(error)
            st.session_state.messages.append({"role": "assistant", "content": error})
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error = "401 Unauthorized – wrong username/password"
            elif e.response.status_code == 404:
                error = "404 Model not found – did you run `ollama pull gemma3`?"
            else:
                error = f"HTTP {e.response.status_code} – {e.response.text[:200]}"
            placeholder.error(error)
            st.session_state.messages.append({"role": "assistant", "content": error})
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            placeholder.error(error)
            st.session_state.messages.append({"role": "assistant", "content": error})

# Footer
st.markdown('<div class="footer">gemma3 · Kaggle + ngrok + Streamlit · 2025</div>', unsafe_allow_html=True)
