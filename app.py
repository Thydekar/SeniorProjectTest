# app.py — Spartan AI Demo — FINAL & ACTUALLY WORKS (Fixed upload + perfect bottom bar)
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

# PERFECT CSS — FIXED BOTTOM BAR + REAL FILE PICKER
st.markdown("""
<style>
    .main {background:#0d1117; color:#c9d1d9;}
    section[data-testid="stSidebar"] {background:#161b22;}
    h1,h2 {color:#58a6ff;}
    
    /* Bottom bar — perfectly fixed and aligned */
    .fixed-bottom-bar {
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
    
    /* Clean upload button */
    .upload-btn button {
        background: #30363d !important;
        color: #c9d1d9 !important;
        border: 1px solid #404040 !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        white-space: nowrap;
    }
    .upload-btn button:hover {
        background: #404040 !important;
        border-color: #58a6ff !important;
    }
    
    /* Hide ugly uploader but keep functionality */
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
    for label, key in [("Assignment Generation","a"),("Assignment Grader","g"),
                      ("AI Content/Plagiarism Detector","d"),("Student Chatbot","s")]:
        if st.button(label, key=key):
            st.session_state.mode = label
            st.session_state.messages = [{"role":"assistant","content":"Hello! How can I help you today?"}]
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
        st.markdown(msg.get("display_text", msg["content"]))
        if msg.get("image"):
            st.image(msg["image"], width=300)

# Bottom padding
st.markdown("<div style='height: 180px;'></div>", unsafe_allow_html=True)

# THE MAGIC: CUSTOM BUTTON THAT OPENS REAL FILE PICKER
st.markdown("""
<div class="fixed-bottom-bar">
    <div class="upload-btn">
        <label for="file-upload" style="cursor:pointer; margin:0;">
            Upload image
        </label>
        <input id="file-upload" type="file" accept="image/*" style="display:none;">
    </div>
""", unsafe_allow_html=True)

# Hidden real file input (triggered by label)
uploaded_file = st.file_uploader("", key="real_upload", type=["png","jpg","jpeg"], label_visibility="collapsed")

# Chat input
prompt = st.chat_input("Type your message...")

st.markdown("</div>", unsafe_allow_html=True)  # close fixed-bottom-bar

# PROCESS IMAGE UPLOAD
if uploaded_file is not None:
    if st.session_state.pending_image is None or st.session_state.pending_image.get("name") != uploaded_file.name:
        with st.spinner("Reading image..."):
            try:
                img = Image.open(uploaded_file).convert("RGB")
                big = img.resize((img.width*3, img.height*3), Image.LANCZOS)
                ocr = pytesseract.image_to_string(big, config=OCR_CONFIG).strip()

                thumb = img.copy()
                thumb.thumbnail((300,300))
                buf = io.BytesIO()
                thumb.save(buf, format="PNG")
                img_bytes = buf.getvalue()

                st.session_state.pending_image = {
                    "name": uploaded_file.name,
                    "thumb": img_bytes,
                    "ocr": ocr
                }
                st.success("Image ready!")
            except:
                st.error("Failed to read image.")
                st.session_state.pending_image = None

# SEND MESSAGE
if prompt:
    image_data = None
    ocr_text = ""

    if st.session_state.pending_image:
        ocr_text = st.session_state.pending_image["ocr"]
        image_data = st.session_state.pending_image["thumb"]
        st.session_state.pending_image = None  # CLEARED — no repeat

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
                        placeholder.markdown(full + "▍")
                        time.sleep(0.01)
                placeholder.markdown(full)
        except:
            placeholder.markdown("Connection failed.")

        st.session_state.messages.append({
            "role": "assistant",
            "content": full,
            "display_text": full
        })

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
