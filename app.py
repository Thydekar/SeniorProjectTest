# app.py — Spartan AI Demo — FINAL & PERFECT (No repeated image, clean bar, no green icon)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image
import io

# CONFIG
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"
MODEL_ASSIGNMENT_GEN = "gemma3"
MODEL_GRADER         = "spartan-grader"
MODEL_PLAGIARISM     = "spartan-detector"
MODEL_STUDENT_CHAT   = "spartan-student"

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
OCR_CONFIG = r"--oem 3 --psm 6"

st.set_page_config(page_title="Spartan AI Demo", layout="centered")

# CLEAN, PROFESSIONAL CSS — NO GREEN ICON, NO GHOST BAR
st.markdown("""
<style>
    .main {background:#0d1117; color:#c9d1d9;}
    section[data-testid="stSidebar"] {background:#161b22;}
    
    /* Fixed bottom bar — clean, flush, no extra lines */
    .chat-bar {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        background: #0d1117;
        border-top: 1px solid #30363d;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 99999;
    }
    
    /* Clean upload button — no icon, just text */
    .upload-btn button {
        background: #30363d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 10px 18px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    .upload-btn button:hover {
        background: #404040 !important;
        border-color: #58a6ff !important;
    }
    
    /* Hide all file uploader visuals */
    .stFileUploader {display: none !important;}
    
    .footer {
        text-align: center;
        color: #8b949e;
        font-size: 0.85em;
        margin-top: 60px;
        padding-bottom: 180px;
    }
    h1, h2 {color: #58a6ff;}
</style>
""", unsafe_allow_html=True)

# STATE
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_image" not in st.session_state:
    st.session_state.pending_image = None
if "mode" not in st.session_state:
    st.session_state.mode = "Home"

# SIDEBAR
with st.sidebar:
    st.title("Spartan AI Demo")
    if st.button("Home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.session_state.pending_image = None
        st.rerun()

    st.markdown("**Tools**")
    tools = [
        ("Assignment Generation", "a"),
        ("Assignment Grader", "g"),
        ("AI Content/Plagiarism Detector", "d"),
        ("Student Chatbot", "s")
    ]
    for label, key in tools:
        if st.button(label, key=key):
            st.session_state.mode = label
            st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
            st.session_state.pending_image = None
            st.rerun()
    st.markdown("---")
    st.caption("Senior Project by Dallin Geurts")

mode = st.session_state.mode
model_map = {
    "Assignment Generation": MODEL_ASSIGNMENT_GEN,
    "Assignment Grader": MODEL_GRADER,
    "AI Content/Plagiarism Detector": MODEL_PLAGIARISM,
    "Student Chatbot": MODEL_STUDENT_CHAT
}

# HOME PAGE
if mode == "Home":
    st.title("Spartan AI Demo")
    st.markdown("### Empowering Education with Responsible AI")
    st.markdown("""
    **Spartan AI** is a senior project by **Dallin Geurts** designed to support teachers and students with ethical, powerful AI tools.
    """)
    st.markdown("### Tools")
    st.markdown("• Assignment Generation\n• Assignment Grader\n• AI Content/Plagiarism Detector\n• Student Chatbot")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

current_model = model_map[mode]
st.title(mode)

# CHAT HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg["content"]))
        if msg.get("image"):
            st.image(msg["image"], width=300)

# Bottom padding
st.markdown("<div style='height: 160px;'></div>", unsafe_allow_html=True)

# FIXED BOTTOM BAR — CLEAN & PERFECT
st.markdown("<div class='chat-bar'>", unsafe_allow_html=True)

# Upload button (triggers hidden uploader)
with st.container():
    col1, col2 = st.columns([1.8, 8])
    with col1:
        if st.button("Upload image", key="upload_trigger"):
            pass  # Just triggers rerun to show uploader
    with col2:
        prompt = st.chat_input("Type your message...")

st.markdown("</div>", unsafe_allow_html=True)

# Hidden file uploader — appears only when button clicked
if st.session_state.get("upload_triggered", False):
    uploaded_file = st.file_uploader(
        "Select image",
        type=["png", "jpg", "jpeg"],
        key="real_uploader",
        label_visibility="collapsed"
    )
else:
    uploaded_file = None

# Trigger uploader visibility
if st.button("Upload image", key="upload_trigger"):
    st.session_state.upload_triggered = True

# Process uploaded image
if uploaded_file:
    if st.session_state.pending_image is None or st.session_state.pending_image.get("name") != uploaded_file.name:
        with st.spinner("Reading image..."):
            try:
                img = Image.open(uploaded_file).convert("RGB")
                big = img.resize((img.width*3, img.height*3), Image.LANCZOS)
                ocr = pytesseract.image_to_string(big, config=OCR_CONFIG).strip()

                thumb = img.copy()
                thumb.thumbnail((300, 300))
                buf = io.BytesIO()
                thumb.save(buf, format="PNG")
                img_bytes = buf.getvalue()

                st.session_state.pending_image = {
                    "name": uploaded_file.name,
                    "thumb": img_bytes,
                    "ocr": ocr
                }
                st.success("Image ready!")
                st.session_state.upload_triggered = False  # hide uploader
            except:
                st.error("Failed to read image.")
                st.session_state.pending_image = None

# SEND MESSAGE
if prompt:
    image_data = None
    ocr_text = ""

    # Use image ONLY if pending, then CLEAR IT
    if st.session_state.pending_image:
        ocr_text = st.session_state.pending_image["ocr"]
        image_data = st.session_state.pending_image["thumb"]
        st.session_state.pending_image = None  # CRITICAL: cleared after first use

    user_content = f"user-query{{{prompt}}}"
    if ocr_text:
        user_content = f"uploaded-image-text{{{ocr_text}}}\n{user_content}"

    st.session_state.messages.append({
        "role": "user",
        "content": user_content,
        "display_text": prompt,
        "image": image_data
    })

    with st.chat_message("user"):
        st.markdown(prompt)
        if image_data:
            st.image(image_data, width=300)

    # AI RESPONSE
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            payload = {
                "model": current_model,
                "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                "stream": True
            }
            with requests.post(
                OLLAMA_CHAT_URL, json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600, verify=False, stream=True
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        full_response += token
                        placeholder.markdown(full_response + "▍")
            placeholder.markdown(full_response)
        except:
            full_response = "Sorry, I couldn't connect."
            placeholder.markdown(full_response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "display_text": full_response
        })

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
