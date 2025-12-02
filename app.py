# app.py — Spartan AI Demo — Senior Project by Dallin Geurts
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image
import io

# ─────────────────────────── EDIT THESE ONLY ───────────────────────────
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"  # ← Your permanent tunnel

# MODEL NAMES — CHANGE THESE WHEN YOU TRAIN NEW MODELS
MODEL_ASSIGNMENT_GEN   = "spartan-assignment"      # Assignment Generator
MODEL_GRADER           = "spartan-grader"          # Assignment Grader
MODEL_PLAGIARISM       = "spartan-detector"        # AI Content / Plagiarism Detector
MODEL_STUDENT_CHAT     = "spartan-student"         # Student Helper Chatbot
# ───────────────────────────────────────────────────────────────────────

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"

# OCR Setup (for image uploads)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Kaggle has it installed

st.set_page_config(
    page_title="Spartan AI Demo",
    page_icon="Shield",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Professional Dark Theme
st.markdown("""
<style>
    .main {background: #0d1117; color: #c9d1d9;}
    .stApp {background: #0d1117;}
    section[data-testid="stSidebar"] {background: #161b22; border-right: 1px solid #30363d;}
    .stChatMessage {margin: 12px 0;}
    .stTextInput > div > div > input {background: #21262d; color: white; border: 1px solid #30363d; border-radius: 16px;}
    .stButton > button {background: #238636; color: white; border-radius: 16px; height: 48px; font-weight: 600;}
    .ocr-box {background: #1e1e2e; padding: 12px; border-radius: 10px; border: 1px solid #30363d; font-size: 0.9em;}
    .footer {text-align: center; color: #8b949e; font-size: 0.85em; margin-top: 60px; padding: 20px;}
    h1, h2, h3 {color: #58a6ff;}
    .css-1d391kg {padding-top: 1rem;}
</style>
""", unsafe_allow_html=True)

# ────────────────────────── SIDEBAR & NAVIGATION ──────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/100/shield.png", width=80)
    st.title("Spartan AI Demo")
    st.markdown("**Select AI Assistant**")

    mode = st.radio(
        "Choose Tool",
        [
            "Assignment Generation",
            "Assignment Grader",
            "AI Content/Plagiarism Detector",
            "Student Chatbot"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("Senior Project by Dallin Geurts")

# Map mode to model
model_map = {
    "Assignment Generation": MODEL_ASSIGNMENT_GEN,
    "Assignment Grader": MODEL_GRADER,
    "AI Content/Plagiarism Detector": MODEL_PLAGIARISM,
    "Student Chatbot": MODEL_STUDENT_CHAT
}
current_model = model_map[mode]

# ───────────────────────────── HOME PAGE ─────────────────────────────
if len(st.session_state.get("messages", [])) == 0 and not st.session_state.get("started", False):
    st.title("Shield Spartan AI Demo")
    st.markdown("### Empowering Education with Responsible AI")

    st.markdown("""
    **Spartan AI** is a senior project developed by **Dallin Geurts** to enhance teaching and learning through carefully designed artificial intelligence tools.

    This suite of assistants helps teachers streamline workflow — generating high-quality assignments, providing fair and consistent grading, and detecting AI-generated content — while giving students a safe, ethical chatbot that encourages learning rather than shortcutting it.

    Unlike general-purpose AI tools that can be misused to complete homework or write essays, Spartan AI is built from the ground up with **educational integrity** in mind. It assists without replacing thought, effort, or growth.

    All models are fine-tuned and moderated to support academic honesty and meaningful learning.
    """)

    st.markdown("### Available Tools")
    st.markdown("""
    - **Assignment Generation** – Create original, leveled assignments instantly  
    - **Assignment Grader** – Grade submissions with detailed, fair feedback  
    - **AI Content/Plagiarism Detector** – Identify AI-written text in student work  
    - **Student Chatbot** – Help students understand concepts (won’t write essays for them)
    """)

    if st.button("Begin Using Spartan AI", type="primary", use_container_width=True):
        st.session_state.started = True
        st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

# ───────────────────────────── CHAT INTERFACE ─────────────────────────────
st.title(f"{mode}")

# Image Upload + OCR
uploaded_file = st.file_uploader("Upload an image (handwriting, screenshot, etc.)", type=["png", "jpg", "jpeg"])
ocr_text = ""

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", width=400)
    with st.spinner("Reading text from image..."):
        try:
            ocr_text = pytesseract.image_to_string(image)
            st.success("Text extracted from image!")
            st.markdown(f"<div class='ocr-box'><strong>OCR Result:</strong><br>{ocr_text}</div>", unsafe_allow_html=True)
        except:
            st.error("OCR failed. Try a clearer image.")

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
prompt = st.chat_input("Type your message or ask about the uploaded image...")

if prompt or (uploaded_file and ocr_text):
    user_message = prompt or ""
    if ocr_text:
        user_message = f"[IMAGE UPLOADED]\n\nText from image:\n\"\"\"\n{ocr_text.strip()}\n\"\"\"\n\n{user_message}".strip()

    st.session_state.messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

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
                            chunk = json.loads(line.decode())
                            token = chunk.get("message", {}).get("content", "")
                            full_response += token
                            placeholder.markdown(full_response + "▎")
                            time.sleep(0.008)
                        except:
                            continue
                placeholder.markdown(full_response)

        except Exception as e:
            error_msg = "I'm having trouble connecting right now. Please try again in a moment."
            placeholder.error(error_msg)
            full_response = error_msg

        st.session_state.messages.append({"role": "assistant", "content": full_response})

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project by Dallin Geurts • Built for Education</div>", unsafe_allow_html=True)
