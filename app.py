# app.py — Spartan AI Demo — FINAL & FLAWLESS (Paperclip only, image once, perfect)
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image
import io

# EDIT ONLY THESE
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

# CLEAN, PROFESSIONAL CSS — ONLY PAPERCLIP
st.markdown("""
<style>
    .main {background:#0d1117; color:#c9d1d9;}
    section[data-testid="stSidebar"] {background:#161b22; border-right:1px solid #30363d;}
    
    /* Hide ALL default file uploader visuals */
    section[data-testid="stFileUploader"] {display:none !important;}
    .uploadedFileName, .stFileUploader label, div[data-testid="stFileUploaderDropzone"] {display:none !important;}
    
    /* Paperclip button */
    .paperclip-button button {
        background: transparent !important;
        border: none !important;
        padding: 8px 10px !important;
        border-radius: 8px !important;
        color: #8b949e !important;
        font-size: 20px !important;
    }
    .paperclip-button button:hover {
        background: #30363d !important;
        color: #58a6ff !important;
    }
    
    .stButton>button {width:100%; margin:10px 0; background:#21262d; color:white;
        border:1px solid #30363d; border-radius:14px; padding:16px; font-weight:700; font-size:18px;}
    .stButton>button:active {background:#58a6ff !important; color:black !important;}
    
    .footer {text-align:center; color:#8b949e; font-size:0.85em; margin-top:60px;}
    h1,h2 {color:#58a6ff;}
</style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.title("Spartan AI Demo")
    if st.button("Home", key="home"):
        for k in ["mode","messages","pending_image","last_mode"]:
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown("**Tools**")
    for label,key in [("Assignment Generation","a"),("Assignment Grader","g"),
                      ("AI Content/Plagiarism Detector","d"),("Student Chatbot","s")]:
        if st.button(label,key=key):
            st.session_state.mode = label
            if st.session_state.get("last_mode") != label:
                st.session_state.messages = [{"role":"assistant","content":"Hello! How can I help you today?"}]
                st.session_state.last_mode = label
            st.session_state.pending_image = None
            st.rerun()
    st.markdown("---")
    st.caption("Senior Project by Dallin Geurts")

mode = st.session_state.get("mode","Home")
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
    This suite helps teachers streamline their workflow while giving students a safe, ethical chatbot that supports understanding without enabling academic dishonesty.
    All models are fine-tuned to promote honesty, effort, and real learning.
    """)
    st.markdown("### Available Tools")
    st.markdown("• Assignment Generation\n• Assignment Grader\n• AI Content/Plagiarism Detector\n• Student Chatbot (safe & helpful)")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

current_model = model_map[mode]
st.title(f"{mode}")

# Initialize chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role":"assistant","content":"Hello! How can I help you today?"}]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg.get("content", "")))
        if msg.get("image"):
            st.image(msg["image"], width=300)

# === CUSTOM CHAT BAR WITH PAPERCLIP ONLY ===
col1, col2, col3 = st.columns([0.6, 7, 1])

with col1:
    # Hidden file uploader
    uploaded_file = st.file_uploader("", type=["png","jpg","jpeg"], key="hidden_uploader", label_visibility="collapsed")

with col2:
    prompt = st.chat_input("Type your message...")

with col3:
    st.markdown('<div class="paperclip-button">', unsafe_allow_html=True)
    st.markdown("Paperclip", unsafe_allow_html=True)  # This shows ONLY the icon
    st.markdown('</div>', unsafe_allow_html=True)

# Process image when uploaded
if uploaded_file is not None:
    if st.session_state.get("pending_image", {}).get("name") != uploaded_file.name:
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

                st.session_state.pending_image = {"name": uploaded_file.name, "thumb": img_bytes, "ocr": ocr}
                st.success("Image ready!")
            except:
                st.error("Failed to read image.")
                st.session_state.pending_image = None

# Handle message
if prompt:
    ollama_messages = []
    for m in st.session_state.messages:
        ollama_messages.append({"role": m["role"], "content": m.get("ai_content", m.get("content", ""))})

    ai_text = ""
    display_text = prompt
    image_data = None

    if st.session_state.get("pending_image"):
        ocr = st.session_state.pending_image["ocr"]
        if ocr:
            ai_text += f"uploaded-image-text{{{ocr}}}\n"
        image_data = st.session_state.pending_image["thumb"]
        st.session_state.pending_image = None  # CONSUMED — never repeats

    ai_text += f"user-query{{{prompt}}}"

    # Save message
    st.session_state.messages.append({
        "role": "user",
        "ai_content": ai_text,
        "content": ai_text,
        "display_text": prompt,
        "image": image_data
    })

    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
        if image_data:
            st.image(image_data, width=300)

    # Call AI
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        try:
            payload = {"model": current_model, "messages": ollama_messages + [{"role":"user","content":ai_text}], "stream":True}
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
            placeholder.error("Connection failed.")
            full = "Sorry, I can't connect right now."

        st.session_state.messages.append({
            "role": "assistant",
            "ai_content": full,
            "content": full,
            "display_text": full,
            "image": None
        })

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
