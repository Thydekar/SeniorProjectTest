# app.py — Spartan AI Demo — Final Clean & Professional
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image

# ──────────────────────── EDIT ONLY THESE ────────────────────────
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"

MODEL_ASSIGNMENT_GEN = "spartan-assignment"
MODEL_GRADER         = "spartan-grader"
MODEL_PLAGIARISM     = "spartan-detector"
MODEL_STUDENT_CHAT   = "spartan-student"
# ──────────────────────────────────────────────────────────────────

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"

st.set_page_config(page_title="Spartan AI Demo", layout="centered")

# Clean, modern dark theme + fixed input bar + bold sidebar
st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9; padding-bottom: 100px;}
    .stApp {background: #0d1117;}
    section[data-testid="stSidebar"] {background: #161b22; border-right: 1px solid #30363d;}
    
    /* Sidebar buttons — large, bold, elegant */
    .stButton > button {
        width: 100%; margin: 12px 0; background: #21262d; color: white;
        border: 1px solid #30363d; border-radius: 16px; padding: 18px;
        font-weight: 700; font-size: 19px; transition: all 0.2s;
    }
    .stButton > button:hover {background: #21262d; border-color: #30363d;}
    .stButton > button:active {
        background: #58a6ff !important; color: black !important; border-color: #58a6ff;
    }
    
    /* Hide file uploader by default */
    .uploadedFile {display: none;}
    .stChatInput {position: fixed; bottom: 0; left: 0; right: 0; background: #0d1117; padding: 20px; z-index: 9999; border-top: 1px solid #30363d;}
    .stChatMessage {margin-bottom: 20px;}
    .footer {text-align: center; color: #8b949e; font-size: 0.85em; padding: 20px;}
    h1, h2 {color: #58a6ff;}
</style>
""", unsafe_allow_html=True)

# ────────────────────────── SIDEBAR ──────────────────────────
with st.sidebar:
    st.title("Spartan AI Demo")

    if st.button("Home", key="home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.rerun()

    st.markdown("**Tools**", unsafe_allow_html=True)

    tools = [
        "Assignment Generation",
        "Assignment Grader",
        "AI Content/Plagiarism Detector",
        "Student Chatbot"
    ]

    for tool in tools:
        if st.button(tool, key=tool):
            st.session_state.mode = tool
            if "messages" not in st.session_state or st.session_state.get("last_mode") != tool:
                st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
                st.session_state.last_mode = tool
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
    st.markdown("• Assignment Generation  \n• Assignment Grader  \n• AI Content/Plagiarism Detector  \n• Student Chatbot")

    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

# ───────────────────────────── CHAT INTERFACE ─────────────────────────────
current_model = model_map[mode]
st.title(f"{mode}")

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("image"):
            st.image(msg["image"], width=300)

# Fixed input bar at bottom
with st.container():
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)  # spacer

# Paperclip + input
col1, col2 = st.columns([0.1, 0.9])
with col1:
    if st.button("Paperclip", key="clip"):
        st.session_state.show_uploader = True
with col2:
    prompt = st.chat_input("Ask a question...")

# Hidden file uploader
uploaded_file = None
if st.session_state.get("show_uploader"):
    uploaded_file = st.file_uploader("Upload image", type=["png", "jpg", "jpeg"], key="uploader")
    if uploaded_file is None:
        st.session_state.show_uploader = False
        st.rerun()

# Process input
if prompt or uploaded_file:
    ocr_text = ""
    image_preview = None

    if uploaded_file:
        image = Image.open(uploaded_file)
        image_preview = image.copy()
        image_preview.thumbnail((300, 300))
        with st.chat_message("user"):
            st.image(image_preview, width=300)
            if prompt:
                st.markdown(prompt)

        with st.spinner("Reading image..."):
            try:
                ocr_text = pytesseract.image_to_string(image)
            except:
                ocr_text = ""

    # Build internal message
    internal_msg = ""
    if ocr_text:
        internal_msg += f"uploaded-image-text{{{ocr_text.strip()}}}"
    if prompt:
        internal_msg += f"user-query{{{prompt.strip()}}}"

    # User sees clean version
    user_display = prompt or "Image uploaded"
    st.session_state.messages.append({
        "role": "user",
        "content": user_display,
        "image": image_preview if uploaded_file else None
    })

    # Send to AI
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""

        try:
            payload = {
                "model": current_model,
                "messages": st.session_state.messages[:-1] + [{"role": "user", "content": internal_msg or user_display}],
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
