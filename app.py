# app.py — Spartan AI Demo — FINAL & PROFESSIONAL (Clean upload button)
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

st.markdown("""
<style>
    .main {background:#0d1117; color:#c9d1d9;}
    section[data-testid="stSidebar"] {background:#161b22;}
    .stButton>button {width:100%; margin:10px 0; background:#21262d; color:white;
        border:1px solid #30363d; border-radius:14px; padding:16px; font-weight:700; font-size:18px;}
    .stButton>button:active {background:#58a6ff !important; color:black !important;}
    
    /* Clean upload button */
    .upload-btn button {
        background:#238636 !important;
        color:white !important;
        border:none !important;
        border-radius:12px !important;
        padding:10px 16px !important;
        font-size:14px !important;
    }
    .upload-btn button:hover {background:#2ea043 !important;}
    
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

# Display chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg.get("content", "")))
        if msg.get("image"):
            st.image(msg["image"], width=300)

# CLEAN UPLOAD BUTTON + CHAT INPUT
col1, col2 = st.columns([1.5, 6])

with col1:
    if st.button("Upload image", key="upload_btn"):
        # Trigger hidden file uploader
        st.file_uploader("Select image", type=["png","jpg","jpeg"], key="actual_uploader", label_visibility="collapsed")

with col2:
    prompt = st.chat_input("Type your message...")

# Process uploaded file (from hidden uploader)
uploaded_file = st.session_state.get("actual_uploader")

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
                st.error("Failed to process image.")
                st.session_state.pending_image = None

# Handle message
if prompt:
    ollama_messages = [ {"role": m["role"], "content": m.get("ai_content", m.get("content", ""))} 
                       for m in st.session_state.messages ]

    ai_text = ""
    display_text = prompt
    image_data = None

    if st.session_state.get("pending_image"):
        ocr = st.session_state.pending_image["ocr"]
        if ocr.strip():
            ai_text += f"uploaded-image-text{{{ocr}}}\n"
        image_data = st.session_state.pending_image["thumb"]
        st.session_state.pending_image = None  # consumed

    ai_text += f"user-query{{{prompt}}}"

    # Save user message
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
            full = "Sorry, couldn't connect."

        st.session_state.messages.append({
            "role": "assistant",
            "ai_content": full,
            "content": full,
            "display_text": full,
            "image": None
        })

# Footer
st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
