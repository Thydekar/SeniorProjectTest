# app.py — Spartan AI Demo — Final Professional Version
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

# Clean dark theme + big bold sidebar buttons
st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    .stApp {background: #0d1117;}
    section[data-testid="stSidebar"] {background: #161b22; border-right: 1px solid #30363d;}
    
    /* Sidebar buttons — large, bold, black & blue */
    .stButton > button {
        width: 100%; margin: 10px 0; background: #21262d; color: white;
        border: 1px solid #30363d; border-radius: 14px; padding: 16px;
        font-weight: 700; font-size: 18px; transition: all 0.2s;
    }
    .stButton > button:hover {background: #21262d; border-color: #30363d;}
    .stButton > button:active,
    .stButton > button[data-active="true"] {
        background: #58a6ff !important; color: black !important; border-color: #58a6ff;
    }
    
    .stTextInput > div > div > input {background: #21262d; color: white; border: 1px solid #30363d; border-radius: 16px;}
    .uploaded-image {border-radius: 10px; margin: 10px 0;}
    .footer {text-align: center; color: #8b949e; font-size: 0.85em; margin-top: 60px; padding: 20px;}
    h1, h2 {color: #58a6ff;}
</style>
""", unsafe_allow_html=True)

# ────────────────────────── SIDEBAR WITH HOME + TOOLS ──────────────────────────
with st.sidebar:
    st.title("Spartan AI Demo")

    if st.button("Home", key="home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
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
    st.markdown("""
    • Assignment Generation  
    • Assignment Grader  
    • AI Content/Plagiarism Detector  
    • Student Chatbot (safe & helpful)
    """)

    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

# ───────────────────────────── CHAT INTERFACE ─────────────────────────────
current_model = model_map[mode]
st.title(f"{mode}")

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input with file upload in the bar
with st.container():
    cols = st.columns([0.07, 1])
    with cols[0]:
        uploaded_file = st.file_uploader("", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    with cols[1]:
        prompt = st.chat_input("Ask a question...")

# Process upload + message
if uploaded_file or prompt:
    ocr_text = ""
    image_preview = None

    if uploaded_file:
        image = Image.open(uploaded_file)
        image_preview = image.copy()
        image_preview.thumbnail((300, 300))
        with st.chat_message("user"):
            st.image(image_preview, caption="Image attached", use_column_width=False, output_format="PNG")
            if prompt:
                st.markdown(prompt)
            else:
                st.markdown("*Image uploaded*")

        with st.spinner("Reading text from image..."):
            try:
                ocr_text = pytesseract.image_to_string(image)
            except:
                ocr_text = "[OCR failed — image too blurry or unsupported]"

    # Build internal message (hidden from user)
    internal_message = ""
    if ocr_text:
        internal_message += f"uploaded-image-text{{{ocr_text.strip()}}}"
    if prompt:
        internal_message += f"user-query{{{prompt.strip()}}}"

    # Show only user-facing message
    user_display = prompt or "*Image uploaded*"

    st.session_state.messages.append({"role": "user", "content": user_display})
    if uploaded_file:
        st.session_state.messages[-1]["image"] = image_preview  # for display only

    # Send to AI
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""

        try:
            payload = {
                "model": current_model,
                "messages": st.session_state.messages[:-1] + [{"role": "user", "content": internal_message}],
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

        except Exception as e:
            placeholder.error("Connection lost — please try again.")

        st.session_state.messages.append({"role": "assistant", "content": full})

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
