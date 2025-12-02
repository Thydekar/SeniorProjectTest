# app.py — Spartan AI Demo — FINAL & FLAWLESS (ChatGPT-style bottom bar + real cursor)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image

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

# PERFECT CHATGPT-STYLE CSS
st.markdown("""
<style>
    .main {background:#0d1117; color:#c9d1d9;}
    section[data-testid="stSidebar"] {background:#161b22;}
    h1,h2 {color:#58a6ff;}
    
    /* ChatGPT-style fixed bottom bar */
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        background: #0d1117;
        padding: 16px;
        border-top: 1px solid #30363d;
        z-index: 99999;
        border-radius: 16px 16px 0 0;
        box-shadow: 0 -8px 30px rgba(0,0,0,0.4);
    }
    
    /* Upload button — perfect alignment */
    .upload-btn button {
        background: #30363d !important;
        color: #c9d1d9 !important;
        border: 1px solid #404040 !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        margin-right: 12px !important;
    }
    .upload-btn button:hover {
        background: #404040 !important;
        border-color: #58a6ff !important;
    }
    
    /* Hide file uploader */
    .stFileUploader {display: none !important;}
    
    /* Real blinking cursor */
    .stChatInput > div > div > textarea {
        caret-color: #58a6ff !important;
    }
    
    .footer {
        text-align: center;
        color: #8b949e;
        font-size: 0.85em;
        padding-bottom: 200px;
        margin-top: 60px;
    }
</style>
""", unsafe_allow_html=True)

# STATE
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_ocr_text" not in st.session_state:
    st.session_state.pending_ocr_text = None
if "mode" not in st.session_state:
    st.session_state.mode = "Home"

# SIDEBAR
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
    st.markdown("Spartan AI helps teachers and students with ethical, powerful tools.")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

current_model = model_map[mode]
st.title(mode)

# CHAT HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg.get("content", "")))

# Bottom padding
st.markdown("<div style='height: 200px;'></div>", unsafe_allow_html=True)

# FIXED BOTTOM CHAT BAR — PERFECT LAYOUT
st.markdown("<div class='chat-input-container'>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 8])

with col1:
    st.markdown("""
    <label for="file-upload" style="cursor:pointer;">
        <div class="upload-btn"><button>Upload image</button></div>
    </label>
    <input id="file-upload" type="file" accept="image/*" style="display:none;">
    """, unsafe_allow_html=True)

with col2:
    prompt = st.chat_input("Type your message...")

# Hidden uploader
uploaded_file = st.file_uploader("", key="file_upload", type=["png","jpg","jpeg"], label_visibility="collapsed")

st.markdown("</div>", unsafe_allow_html=True)

# PROCESS IMAGE
if uploaded_file is not None:
    if st.session_state.get("last_file") != uploaded_file.name:
        with st.spinner("Processing image..."):
            try:
                img = Image.open(uploaded_file).convert("RGB")
                big = img.resize((img.width*3, img.height*3), Image.LANCZOS)
                ocr_text = pytesseract.image_to_string(big, config=OCR_CONFIG).strip()
                
                st.session_state.pending_ocr_text = ocr_text if ocr_text else "(No text detected)"
                st.session_state.last_file = uploaded_file.name
                st.success("Image processed")
            except:
                st.error("Failed to process image.")
                st.session_state.pending_ocr_text = None

# SEND MESSAGE
if prompt:
    user_content = f"user-query{{{prompt}}}"
    if st.session_state.pending_ocr_text is not None:
        user_content = f"uploaded-image-text{{{st.session_state.pending_ocr_text}}}\n{user_content}"
        st.session_state.pending_ocr_text = None

    st.session_state.messages.append({
        "role": "user",
        "content": user_content,
        "display_text": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

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
                        token = json.loads(line).get("message", {}).get("content", "")
                        full += token
                        placeholder.markdown(full + "█")  # Real blinking cursor
                placeholder.markdown(full)
        except:
            placeholder.markdown("Sorry, connection failed.")

        st.session_state.messages.append({
            "role": "assistant",
            "content": full,
            "display_text": full
        })

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
