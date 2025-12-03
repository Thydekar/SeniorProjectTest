# app.py - Spartan AI Student Chatbot (Minimal & Perfect)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image
import io

# Graceful imports for file support
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    import docx
except ImportError:
    docx = None

# === CONFIG ===
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"  # ← change if needed
MODEL = "spartan-student"                                            # only this model
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
OCR_CONFIG = r"--oem 3 --psm 6"

st.set_page_config(page_title="Spartan AI • Student Chat", layout="centered")

# === STYLING ===
st.markdown("""
<style>
    .main {background:#0d1117; color:#c9d1d9;}
    h1 {color:#58a6ff; text-align:center;}
    .stChatMessage.user {background:#f85149 !important; color:white !important;}
    .stChatMessage.assistant {background:#f0ad4e !important; color:black !important;}
    
    .bottom-bar {
        position:fixed; bottom:0; left:50%; transform:translateX(-50%);
        width:90%; max-width:900px; background:#0d1117;
        border-top:1px solid #30363d; padding:16px 20px;
        display:flex; align-items:center; gap:12px; z-index:9999;
        border-radius:16px 16px 0 0; box-shadow:0 -4px 20px rgba(0,0,0,0.3);
    }
    .new-chat-btn button {
        background:#238636 !important; color:white !important;
        border:none !important; border-radius:12px !important;
        padding:12px 20px !important; font-weight:600 !important;
    }
    .new-chat-btn button:hover {background:#2ea043 !important;}
    
    .thinking {font-size:1.2em; font-weight:bold; color:#58a6ff;}
    .dot {animation: blink 1.4s infinite both;}
    .dot:nth-child(1){animation-delay:0s;}
    .dot:nth-child(2){animation-delay:0.2s;}
    .dot:nth-child(3){animation-delay:0.4s;}
    @keyframes blink {0%,80%,100%{opacity:0.3;} 20%{opacity:1;}}
</style>
""", unsafe_allow_html=True)

# === SESSION STATE ===
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your Spartan AI assistant. How can I help you today?"}]
if "pending_text" not in st.session_state:
    st.session_state.pending_text = None
if "last_file" not in st.session_state:
    st.session_state.last_file = None

# === HEADER ===
st.markdown("<h1>Spartan AI • Student Chatbot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8b949e;'>Ask anything • Upload files • Private & local AI</p>", unsafe_allow_html=True)
st.markdown("---")

# === CHAT HISTORY ===
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg["content"]))

# Padding so content isn’t hidden under bottom bar
st.markdown("<div style='height:130px;'></div>", unsafe_allow_html=True)

# === BOTTOM BAR ===
st.markdown("<div class='bottom-bar'>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([2, 2, 6])

with col1:
    if st.button("New Chat", key="new_chat"):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your Spartan AI assistant. How can I help you today?"}]
        st.session_state.pending_text = None
        st.session_state.last_file = None
        st.rerun()

with col2:
    uploaded = st.file_uploader("Upload", type=["pdf","docx","txt","png","jpg","jpeg"], label_visibility="collapsed")

with col3:
    prompt = st.chat_input("Type your message...")

st.markdown("</div>", unsafe_allow_html=True)

# === FILE PROCESSING ===
if uploaded and uploaded.name != st.session_state.last_file:
    with st.spinner("Reading file..."):
        text = ""
        ext = uploaded.name.split(".")[-1].lower()
        try:
            if ext == "pdf" and PyPDF2:
                reader = PyPDF2.PdfReader(uploaded)
                for page in reader.pages:
                    t = page.extract_text()
                    if t: text += t + "\n"
            elif ext == "docx" and docx:
                doc = docx.Document(uploaded)
                text = "\n".join(p.text for p in doc.paragraphs)
            elif ext == "txt":
                text = uploaded.read().decode("utf-8", errors="ignore")
            elif ext in ["png","jpg","jpeg"]:
                img = Image.open(uploaded).convert("RGB")
                text = pytesseract.image_to_string(img, config=OCR_CONFIG)
            
            text = text.strip() or "(No text found)"
            st.session_state.pending_text = text
            st.session_state.last_file = uploaded.name
            st.success("File ready!")
        except:
            st.error("Couldn’t read file.")
            st.session_state.pending_text = None

# === SEND MESSAGE ===
if prompt:
    # Add file text if present
    if st.session_state.pending_text:
        full_prompt = f"uploaded-file-text{{{st.session_state.pending_text}}}\nuser-query{{{prompt}}}"
        st.session_state.pending_text = None
    else:
        full_prompt = f"user-query{{{prompt}}}"

    st.session_state.messages.append({"role": "user", "content": full_prompt, "display_text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI RESPONSE WITH THINKING → TYPING CURSOR
    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.markdown('<div class="thinking">Thinking<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span></div>', unsafe_allow_html=True)

        placeholder = st.empty()
        answer = ""

        try:
            payload = {
                "model": MODEL,
                "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                "stream": True
            }
            with requests.post(
                OLLAMA_CHAT_URL, json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600, verify=False, stream=True
            ) as r:
                r.raise_for_status()
                first = True
                for line in r.iter_lines():
                    if line:
                        token = json.loads(line).get("message", {}).get("content", "")
                        answer += token
                        if first:
                            thinking.empty()
                            first = False
                        placeholder.markdown(answer + "▋", unsafe_allow_html=True)
                        time.sleep(0.01)
                placeholder.markdown(answer)
        except:
            thinking.empty()
            placeholder.markdown("Sorry, I couldn't connect.")

        st.session_state.messages.append({"role": "assistant", "content": answer, "display_text": answer})

# === FOOTER ===
st.markdown("<p style='text-align:center; color:#555; margin-top:50px;'>Spartan AI • Senior Project • Dallin Geurts • 2025</p>", unsafe_allow_html=True)
