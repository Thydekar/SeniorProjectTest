# app.py — Spartan AI Demo — FINAL & EXACTLY WHAT YOU WANTED
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image

# =============================
# CONFIG — EDIT ONLY THESE
# =============================
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

# =============================
# CLEAN PROFESSIONAL CSS
# =============================
st.markdown("""
<style>
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
    }
    
    /* Upload button */
    .upload-btn button {
        background: #30363d !important;
        color: #c9d1d9 !important;
        border: 1px solid #404040 !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    .upload-btn button:hover {
        background: #404040 !important;
        border-color: #58a6ff !important;
    }
    
    /* Hide file uploader completely */
    .stFileUploader {display: none !important;}
    
    .footer {
        text-align: center;
        color: #8b949e;
        font-size: 0.85em;
        padding-bottom: 180px;
        margin-top: 60px;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# SESSION STATE
# =============================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_ocr_text" not in st.session_state:
    st.session_state.pending_ocr_text = None
if "mode" not in st.session_state:
    st.session_state.mode = "Home"

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.title("Spartan AI Demo")
    if st.button("Home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.session_state.pending_ocr_text = None
        st.rerun()

    st.markdown("**Tools**")
    for label, key in [("Assignment Generation","a"),("Assignment Grader","g"),
                      ("AI Content/Plagiarism Detector","d"),("Student Chatbot","s")]:
        if st.button(label, key=key):
            st.session_state.mode = label
            st.session_state.messages = [{"role":"assistant","content":"Hello! How can I help you today?"}]
            st.session_state.pending_ocr_text = None
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

if mode == "Home":
    st.title("Spartan AI Demo")
    st.markdown("### Empowering Education with Responsible AI")
    st.markdown("Spartan AI helps teachers and students with ethical AI tools.")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

current_model = model_map[mode]
st.title(mode)

# =============================
# DISPLAY CHAT (no images shown)
# =============================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["display_text"])

# Bottom padding
st.markdown("<div style='height: 180px;'></div>", unsafe_allow_html=True)

# =============================
# BOTTOM BAR — UPLOAD + CHAT INPUT
# =============================
st.markdown("<div class='bottom-bar'>", unsafe_allow_html=True)

# Custom upload button (triggers hidden uploader)
st.markdown("""
<label for="hidden-uploader" style="cursor:pointer;">
    <div class="upload-btn">
        <button>Upload image</button>
    </div>
</label>
<input id="hidden-uploader" type="file" accept="image/*" style="display:none;">
""", unsafe_allow_html=True)

# Hidden file uploader
uploaded_file = st.file_uploader("", key="hidden_upload", type=["png","jpg","jpeg"], label_visibility="collapsed")

# Chat input
prompt = st.chat_input("Type your message...")

st.markdown("</div>", unsafe_allow_html=True)

# =============================
# PROCESS UPLOADED IMAGE (OCR silently)
# =============================
if uploaded_file is not None:
    if st.session_state.pending_ocr_text is None or st.session_state.get("last_uploaded") != uploaded_file.name:
        with st.spinner("Processing image..."):
            try:
                img = Image.open(uploaded_file).convert("RGB")
                big = img.resize((img.width*3, img.height*3), Image.LANCZOS)
                ocr_text = pytesseract.image_to_string(big, config=OCR_CONFIG).strip()
                
                st.session_state.pending_ocr_text = ocr_text if ocr_text else "(No text found)"
                st.session_state.last_uploaded = uploaded_file.name
                st.success("Image processed")
            except:
                st.error("Failed to process image.")
                st.session_state.pending_ocr_text = None

# =============================
# SEND MESSAGE
# =============================
if prompt:
    # Build message content
    user_content = f"user-query{{{prompt}}}"
    
    if st.session_state.pending_ocr_text:
        user_content = f"uploaded-image-text{{{st.session_state.pending_ocr_text}}}\n{user_content}"
        st.session_state.pending_ocr_text = None  # Clear after first use

    # Save message
    st.session_state.messages.append({
        "role": "user",
        "content": user_content,
        "display_text": prompt
    })

    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        try:
            payload = {
                "model": current_model,
                "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                "stream": True
            }
            with requests.post(OLLAMA_CHAT_URL, json=payload,
                               auth=HTTPBasicAuth(USERNAME, PASSWORD),
                               timeout=600, verify=False, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        token = json.loads(line).get("message",{}).get("content","")
                        full += token
                        placeholder.markdown(full + "cursor")
                        time.sleep(0.01)
                placeholder.markdown(full)
        except:
            full = "Sorry, I couldn't connect right now."
            placeholder.markdown(full)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full,
            "display_text": full
        })

# =============================
# FOOTER
# =============================
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
