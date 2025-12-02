# app.py — Spartan AI Demo (Final Fixed Version)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image

# =============================
# CONFIG
# =============================
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"
MODEL_MAP = {
    "Assignment Generation": "gemma3",
    "Assignment Grader": "spartan-grader",
    "AI Content/Plagiarism Detector": "spartan-detector",
    "Student Chatbot": "spartan-student",
}

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
OCR_CONFIG = r"--oem 3 --psm 6"

st.set_page_config(page_title="Spartan AI Demo", layout="centered")

# =============================
# CSS (BOTTOM BAR FIXED)
# =============================
CSS = """
<style>
    html, body, [data-testid="stAppViewContainer"] {
        padding: 0 !important;
        margin: 0 !important;
        height: 100%;
        background: #0d1117 !important;
        color: #c9d1d9 !important;
    }

    /* Remove Streamlit's built-in chat padding */
    .stChatInputContainer {
        padding-bottom: 0 !important;
    }

    .main {background:#0d1117; color:#c9d1d9;}
    section[data-testid="stSidebar"] {background:#161b22;}
    h1,h2 {color:#58a6ff;}

    /* Fixed bottom bar */
    .bottom-bar {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        background: #0d1117;
        border-top: 1px solid #30363d;
        padding: 14px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 99999;
        border-radius: 16px 16px 0 0;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.3);
    }

    .upload-btn button {
        background:#30363d !important;
        color:#c9d1d9 !important;
        border-radius:12px !important;
        border:1px solid #404040 !important;
        padding:10px 24px !important;
        font-size:14px;
    }
    .upload-btn button:hover {
        background:#404040 !important;
        border-color:#58a6ff !important;
    }

    .stFileUploader {display:none !important;}

    .footer {
        text-align:center;
        color:#8b949e;
        font-size:0.85em;
        margin-top: 80px;
        padding-bottom:160px;
    }

    /* Blinking cursor on assistant messages */
    .stChatMessage assistant::after {
        content:"";
        animation: blink 1s step-end infinite;
    }
    @keyframes blink { 50% {opacity:0;} }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =============================
# SESSION STATE
# =============================
st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending_ocr_text", None)
st.session_state.setdefault("last_uploaded", None)
st.session_state.setdefault("mode", "Home")
st.session_state.setdefault("show_uploader", False)

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.title("Spartan AI Demo")

    if st.button("Home"):
        st.session_state.update(
            messages=[],
            pending_ocr_text=None,
            mode="Home",
            show_uploader=False
        )
        st.rerun()

    st.subheader("Tools")
    for label in MODEL_MAP.keys():
        if st.button(label):
            st.session_state.update(
                mode=label,
                messages=[{"role": "assistant", "content": "Hello! How can I help you today?"}],
                pending_ocr_text=None,
                show_uploader=False
            )
            st.rerun()

    st.markdown("---")
    st.caption("Senior Project by Dallin Geurts")

# =============================
# HOME PAGE
# =============================
if st.session_state.mode == "Home":
    st.title("Spartan AI Demo")
    st.markdown("### Empowering Education with Responsible AI")
    st.markdown("Spartan AI helps teachers and students with ethical, powerful tools.")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>",
                unsafe_allow_html=True)
    st.stop()

# =============================
# TOOL PAGE
# =============================
current_model = MODEL_MAP[st.session_state.mode]
st.title(st.session_state.mode)

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg["content"]))

# =============================
# FIXED BOTTOM BAR
# =============================
st.markdown("<div class='bottom-bar'>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 8])

with col1:
    if st.button("Upload image", key="upload_trigger"):
        st.session_state.show_uploader = True

with col2:
    prompt = st.chat_input("Type your message...")

st.markdown("</div>", unsafe_allow_html=True)

# =============================
# FILE UPLOADER LOGIC
# =============================
uploaded_file = None
if st.session_state.show_uploader:
    uploaded_file = st.file_uploader(
        "Select image", type=["png", "jpg", "jpeg"],
        key="image_uploader",
        label_visibility="collapsed"
    )

# =============================
# OCR PROCESSING
# =============================
if uploaded_file and st.session_state.last_uploaded != uploaded_file.name:
    with st.spinner("Processing image..."):
        try:
            img = Image.open(uploaded_file).convert("RGB")
            ocr = pytesseract.image_to_string(img, config=OCR_CONFIG).strip() or "(No text found)"
            st.session_state.pending_ocr_text = ocr
            st.session_state.last_uploaded = uploaded_file.name
            st.session_state.show_uploader = False

            st.success("Image processed!")
            st.rerun()

        except Exception as e:
            st.error(f"OCR error: {e}")
            st.session_state.pending_ocr_text = None
            st.session_state.show_uploader = False

# =============================
# MESSAGE SEND
# =============================
if prompt:
    # Attach OCR text if available
    if st.session_state.pending_ocr_text:
        full_content = (
            f"uploaded-image-text{{{st.session_state.pending_ocr_text}}}\n"
            f"user-query{{{prompt}}}"
        )
        st.session_state.pending_ocr_text = None
    else:
        full_content = f"user-query{{{prompt}}}"

    # Record user message
    st.session_state.messages.append({
        "role": "user",
        "content": full_content,
        "display_text": prompt
    })

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_reply = ""

        payload = {
            "model": current_model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            "stream": True
        }

        try:
            with requests.post(
                OLLAMA_CHAT_URL, json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600, verify=False, stream=True
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    token = json.loads(line).get("message", {}).get("content", "")
                    full_reply += token
                    placeholder.markdown(full_reply + " ")
                    time.sleep(0.01)
            placeholder.markdown(full_reply)

        except Exception as e:
            placeholder.markdown(f"Connection error: {e}")

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_reply,
            "display_text": full_reply
        })

# =============================
# FOOTER
# =============================
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>",
            unsafe_allow_html=True)
