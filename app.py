# app.py - Spartan AI Student Chatbot (Minimal Final Version)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image

# Graceful imports for PDFs/DOCX
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    import docx
except ImportError:
    docx = None

# Config — ONLY Student Model
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"
MODEL = "spartan-student"
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
OCR_CONFIG = r"--oem 3 --psm 6"

st.set_page_config(page_title="Spartan AI - Student Chatbot", layout="wide")

# Beautiful CSS (kept exactly as you love it)
st.markdown("""
<style>
    body, .css-18e3th9 {background-color: #0d1117 !important; color: #c9d1d9 !important;}
    section[data-testid="stSidebar"] {background-color: #161b22 !important;}
    h1, h2, h3 {color: #58a6ff !important;}
    .stFileUploader > div {background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px !important;}
    .stChatMessage.user {background-color: #f85149 !important; border-radius: 12px !important; color: white !important;}
    .stChatMessage.assistant {background-color: #f0ad4e !important; border-radius: 12px !important; color: black !important;}
    footer {visibility: hidden;}
    .footer-text {text-align: center; color: #8b949e; font-size: 0.85em; padding: 20px 0;}

    /* New Chat button — top left, exactly as before */
    .new-chat-btn {
        position: fixed;
        top: 20px;
        left: 20px;
        z-index: 9999;
        background: #238636 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .new-chat-btn:hover {background: #2ea043 !important;}

    /* Thinking animation */
    .thinking {display: inline-block; font-size: 1.2em; font-weight: bold; color: #58a6ff;}
    .dot {animation: blink 1.4s infinite both;}
    .dot:nth-child(1) {animation-delay: 0s;}
    .dot:nth-child(2) {animation-delay: 0.2s;}
    .dot:nth-child(3) {animation-delay: 0.4s;}
    @keyframes blink {0%, 80%, 100% {opacity: 0.3;} 20% {opacity: 1;}}
</style>
""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your Spartan AI study buddy. How can I help you today?"}]
if "pending_ocr_text" not in st.session_state:
    st.session_state.pending_ocr_text = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# === NEW CHAT BUTTON (top-left, unchanged) ===
if st.button("New Chat", key="new_chat_btn"):
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I'm your Spartan AI study buddy. How can I help you today?"}]
    st.session_state.pending_ocr_text = None
    st.session_state.uploaded_file_name = None
    st.rerun()

# Title
st.title("Spartan AI — Student Chatbot")

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg["content"]))

# File uploader
uploaded_file = st.file_uploader(
    "Upload a file (PDF, DOCX, TXT, image, etc.) — I’ll read it for you!",
    type=["pdf","docx","txt","png","jpg","jpeg","gif","bmp","tiff"]
)

# Extract text from uploaded file
if uploaded_file and uploaded_file.name != st.session_state.uploaded_file_name:
    with st.spinner("Reading your file..."):
        text = ""
        ext = uploaded_file.name.split(".")[-1].lower()
        try:
            if ext == "pdf" and PyPDF2:
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text: text += page_text + "\n"
            elif ext == "docx" and docx:
                doc = docx.Document(uploaded_file)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif ext == "txt":
                text = uploaded_file.read().decode("utf-8", errors="ignore")
            elif ext in ["png","jpg","jpeg","gif","bmp","tiff"]:
                img = Image.open(uploaded_file).convert("RGB")
                text = pytesseract.image_to_string(img, config=OCR_CONFIG)
            else:
                text = "(File type not supported)"
            text = text.strip() or "(No text found)"
            st.session_state.pending_ocr_text = text
            st.session_state.uploaded_file_name = uploaded_file.name
            st.success(f"Got it! I’ve read: {uploaded_file.name}")
        except Exception as e:
            st.error("Couldn't read the file.")
            st.session_state.pending_ocr_text = None

# Chat input
user_input = st.chat_input("Ask me anything or paste your homework...")
if user_input:
    # Attach uploaded text if exists
    if st.session_state.pending_ocr_text:
        full_prompt = f"uploaded-file-text{{{st.session_state.pending_ocr_text}}}\nuser-query{{{user_input}}}"
        st.session_state.pending_ocr_text = None
    else:
        full_prompt = f"user-query{{{user_input}}}"

    st.session_state.messages.append({"role": "user", "content": full_prompt, "display_text": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # AI Response — Thinking → disappears → typing with blinking cursor
    with st.chat_message("assistant"):
        thinking = st.empty()
        thinking.markdown('<div class="thinking">Thinking<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span></div>', unsafe_allow_html=True)

        placeholder = st.empty()
        response = ""

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
                        response += token
                        if first:
                            thinking.empty()
                            first = False
                        placeholder.markdown(response + "▋", unsafe_allow_html=True)
                        time.sleep(0.01)
                placeholder.markdown(response)
        except:
            thinking.empty()
            placeholder.markdown("Sorry, I can't connect right now.")

        st.session_state.messages.append({"role": "assistant", "content": response, "display_text": response})

# Footer
st.markdown('<div class="footer-text">Spartan AI • Senior Project • Dallin Geurts • 2025</div>', unsafe_allow_html=True)
