# app.py — Spartan AI Demo — FINAL & BULLETPROOF (OCR works perfectly)
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

# FIXED: No quotes inside config string → no shlex crash
OCR_CONFIG = r"--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:\()[]{}<>-_+=*/\&%$#@!~^|"

st.set_page_config(page_title="Spartan AI Demo", layout="centered")

st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    section[data-testid="stSidebar"] {background: #161b22; border-right: 1px solid #30363d;}
    .stButton > button {
        width: 100%; margin: 10px 0; background: #21262d; color: white;
        border: 1px solid #30363d; border-radius: 14px; padding: 16px;
        font-weight: 700; font-size:18px;
    }
    .stButton > button:hover {background:#21262d;}
    .stButton > button:active {background:#58a6ff !important; color:black !important;}
    .stTextInput > div > div > input {background:#21262d; color:white; border:1px solid #30363d; border-radius:16px;}
    .footer {text-align:center; color:#8b949e; font-size:0.85em; margin-top:60px; padding:20px;}
    .uploaded-img {border-radius:8px; margin-top:8px;}
    h1, h2 {color:#58a6ff;}
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
    for label, key in [
        ("Assignment Generation", "a"),
        ("Assignment Grader", "g"),
        ("AI Content/Plagiarism Detector", "d"),
        ("Student Chatbot", "s")
    ]:
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
    st.markdown("• Assignment Generation  \n• Assignment Grader  n• AI Content/Plagiarism Detector  n• Student Chatbot (safe & helpful)")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

# ───────────────────────────── CHAT INTERFACE ─────────────────────────────
current_model = model_map[mode]
st.title(f"{mode}")

# Top file uploader
uploaded_file = st.file_uploader("Attach image (handwriting, screenshot, etc.)", type=["png", "jpg", "jpeg"])

# Process image when uploaded (no preview yet)
if uploaded_file and (st.session_state.get("pending_image") is None or st.session_state.pending_image["name"] != uploaded_file.name):
    with st.spinner("Reading image text (optimized OCR)..."):
        try:
            image = Image.open(uploaded_file).convert("RGB")
            # 3× upscale + best settings = maximum accuracy
            big = image.resize((image.width * 3, image.height * 3), Image.LANCZOS)
            ocr_text = pytesseract.image_to_string(big, config=OCR_CONFIG)

            # Create small thumbnail for chat
            thumb = image.copy()
            thumb.thumbnail((300, 300))
            buf = io.BytesIO()
            thumb.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            st.session_state.pending_image = {
                "name": uploaded_file.name,
                "data": img_bytes,
                "text": ocr_text.strip()
            }
            st.success("Image uploaded — ready to send with your question")
        except Exception as e:
            st.error("OCR failed. Try a clearer image.")
            st.session_state.pending_image = None

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
prompt = st.chat_input("Type your question...")

if prompt:
    internal_msg = ""
    show_image_in_chat = False
    image_data = None

    # Use pending image if exists
    if st.session_state.get("pending_image"):
        ocr = st.session_state.pending_image["text"]
        if ocr:
            internal_msg += f"uploaded-image-text{{{ocr}}}"
        show_image_in_chat = True
        image_data = st.session_state.pending_image["data"]
        st.session_state.pending_image = None  # clear after use

    # Add user query
    internal_msg += f"\nuser-query{{{prompt}}}"

    # Show user message (with image if uploaded)
    with st.chat_message("user"):
        st.markdown(prompt)
        if show_image_in_chat:
            st.image(image_data, width=300)

    # Send to AI
    st.session_state.messages.append({"role": "user", "content": internal_msg})

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
                            token = json.loads(line).get("message", {}).get("content", "")
                            full += token
                            placeholder.markdown(full + "▎")
                            time.sleep(0.008)
                        except:
                            continue
                placeholder.markdown(full)
        except Exception:
            placeholder.error("Connection lost — please try again.")

        st.session_state.messages.append({"role": "assistant", "content": full})

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
