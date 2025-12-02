# app.py — Spartan AI Demo — FINAL VERSION (Perfect OCR + No Image Preview)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image
import io

# ──────────────────────── EDIT ONLY THESE ────────────────────────
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"

MODEL_ASSIGNMENT_GEN = "gemma3"
MODEL_GRADER         = "spartan-grader"
MODEL_PLAGIARISM     = "spartan-detector"
MODEL_STUDENT_CHAT   = "spartan-student"
# ──────────────────────────────────────────────────────────────────

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"

# Ultra-robust OCR config
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
OCR_CONFIG = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:\'"()[]{}<>-_+=*/\\&%$#@!~`^| '

st.set_page_config(page_title="Spartan AI Demo", layout="centered")

st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    .stApp {background: #0d1117;}
    section[data-testid="stSidebar"] {background: #161b22; border-right: 1px solid #30363d;}
    
    .stButton > button {
        width: 100%; margin: 10px 0; background: #21262d; color: white;
        border: 1px solid #30363d; border-radius: 14px; padding: 16px;
        font-weight: 700 !important; font-size: 18px !important;
    }
    .stButton > button:hover {background: #21262d;}
    .stButton > button:active {background: #58a6ff !important; color: black !important;}
    
    .stTextInput > div > div > input {background: #21262d; color: white; border: 1px solid #30363d; border-radius: 16px;}
    .footer {text-align: center; color: #8b949e; font-size: 0.85em; margin-top: 60px; padding: 20px;}
    .uploaded-img {border-radius: 8px; margin-top: 8px;}
    h1, h2 {color: #58a6ff;}
</style>
""", unsafe_allow_html=True)

# ────────────────────────── SIDEBAR ──────────────────────────
with st.sidebar:
    st.title("Spartan AI Demo")

    if st.button("Home", key="home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.session_state.pending_image = None
        st.rerun()

    st.markdown("**Tools**")

    tools = [
        ("Assignment Generation", "assignment"),
        ("Assignment Grader", "grader"),
        ("AI Content/Plagiarism Detector", "detector"),
        ("Student Chatbot", "student")
    ]

    for label, key in tools:
        if st.button(label, key=key):
            st.session_state.mode = label
            if "messages" not in st.session_state or st.session_state.get("last_mode") != label:
                st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
                st.session_state.last_mode = label
                st.session_state.pending_image = None
            st.rerun()

    st.markdown("---")
    st.caption("Senior Project by Dallin Geurts")

mode = st.session_state.get("mode", "Home")
model_map = {
    "Assignment Generation": MODEL_ASSIGNMENT_GEN,
    "Assignment Grader": MODEL_GRADER,
    "AI Content/Plagiarism Detector": MODEL_PLAGIARISM,
    "Student Chatbot": MODEL_STUDENT_CHAT
}

# ───────────────────────────── HOME PAGE ─────────────────────────────
if mode == "Home":
    st.title("Spartan AI Demo")
    st.markdown("### Empowering Education with Responsible AI")
    st.markdown("""
    **Spartan AI** is a senior project developed by **Dallin Geurts** to enhance teaching and learning through carefully designed artificial intelligence tools.

    This suite helps teachers streamline their workflow — generating high-quality assignments, providing consistent grading, and detecting AI-generated content — while giving students access to a safe, ethical chatbot that supports understanding without enabling academic dishonesty.

    Unlike general AI tools that can be used to complete assignments, Spartan AI is built with **educational integrity** at its core: it assists, explains, and guides — but never does the work for you.

    All models are fine-tuned to promote honesty, effort, and real learning.
    """)
    st.markdown("### Available Tools")
    st.markdown("• Assignment Generation  \n• Assignment Grader  \n• AI Content/Plagiarism Detector  \n• Student Chatbot (safe & helpful)")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

# ───────────────────────────── CHAT INTERFACE ─────────────────────────────
current_model = model_map[mode]
st.title(f"{mode}")

# File uploader (top)
uploaded_file = st.file_uploader("Attach image (handwriting, screenshot, etc.)", type=["png", "jpg", "jpeg"])

# Store image when uploaded
if uploaded_file and (st.session_state.get("pending_image") is None or st.session_state.pending_image["name"] != uploaded_file.name):
    with st.spinner("Processing image for maximum OCR accuracy..."):
        image = Image.open(uploaded_file).convert("RGB")
        # Enhance image for best OCR
        enhanced = image.resize((image.width * 3, image.height * 3), Image.LANCZOS)
        ocr_text = pytesseract.image_to_string(enhanced, config=OCR_CONFIG)
        
        # Create small thumbnail
        thumbnail = image.copy()
        thumbnail.thumbnail((300, 300))
        buffered = io.BytesIO()
        thumbnail.save(buffered, format="PNG")
        img_data = buffered.getvalue()

        st.session_state.pending_image = {
            "name": uploaded_file.name,
            "data": img_data,
            "text": ocr_text.strip()
        }
        st.success("Image uploaded — ready to send with your question")

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
prompt = st.chat_input("Type your question...")

if prompt:
    internal_message = ""
    user_display = prompt

    # Handle pending image
    if st.session_state.get("pending_image"):
        ocr_text = st.session_state.pending_image["text"]
        if ocr_text:
            internal_message += f"uploaded-image-text{{{ocr_text}}}"
        # Show user message with image
        with st.chat_message("user"):
            st.markdown(prompt)
            st.image(st.session_state.pending_image["data"], width=300)
        st.session_state.pending_image = None  # Clear after send
    else:
        with st.chat_message("user"):
            st.markdown(prompt)

    # Add user query
    if internal_message:
        internal_message += f"\nuser-query{{{prompt}}}"
    else:
        internal_message = f"user-query{{{prompt}}}"

    st.session_state.messages.append({"role": "user", "content": internal_message})

    # AI Response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""

        try:
            payload = {
                "model": current_model,
                "messages": st.session_state.messages,
                "stream": True
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
                for line in r.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            full += token
                            placeholder.markdown(full + "▎")
                            time.sleep(0.008)
                        except:
                            continue
                placeholder.markdown(full)

        except Exception:
            placeholder.error("Connection issue — please try again.")

        st.session_state.messages.append({"role": "assistant", "content": full})

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
