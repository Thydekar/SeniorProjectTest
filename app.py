# app.py — Spartan AI Demo — FINAL & 100% CONNECTED
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
        border:1px solid #30363d; border-radius:14px; padding:16px;
        font-weight:700; font-size:18px;}
    .stButton>button:hover {background:#21262d;}
    .stButton>button:active {background:#58a6ff !important; color:black !important;}
    .footer {text-align:center; color:#8b949e; font-size:0.85em; margin-top:60px;}
    .uploaded-img {border-radius:8px; margin-top:8px;}
    h1,h2 {color:#58a6ff;}
</style>
""", unsafe_allow_html=True)

# ────────────────────────── SIDEBAR ──────────────────────────
with st.sidebar:
    st.title("Spartan AI Demo")
    if st.button("Home", key="home"):
        for k in ["mode","messages","pending_image","last_mode"]: st.session_state.pop(k,None)
        st.rerun()
    st.markdown("**Tools**")
    for label,key in [("Assignment Generation","a"),("Assignment Grader","g"),
                      ("AI Content/Plagiarism Detector","d"),("Student Chatbot","s")]:
        if st.button(label, key=key):
            st.session_state.mode = label
            if st.session_state.get("last_mode") != label:
                st.session_state.messages = [{"role":"assistant","content":"Hello! How can I help you today?"}]
                st.session_state.last_mode = label
            st.session_state.pending_image = None
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

if mode == "Home":
    st.title("Spartan AI Demo")
    st.markdown("### Empowering Education with Responsible AI")
    st.markdown("""**Spartan AI** is a senior project developed by **Dallin Geurts** ...""") # (your text here)
    st.markdown("### Available Tools")
    st.markdown("• Assignment Generation\n• Assignment Grader\n• AI Content/Plagiarism Detector\n• Student Chatbot")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts • 2025</div>", unsafe_allow_html=True)
    st.stop()

# ───────────────────────────── CHAT INTERFACE ─────────────────────────────
current_model = model_map[mode]
st.title(f"{mode}")

# File uploader
uploaded_file = st.file_uploader("Attach image (handwriting, screenshot, etc.)", type=["png","jpg","jpeg"])

if uploaded_file and (st.session_state.get("pending_image") is None or 
                     st.session_state.pending_image["name"] != uploaded_file.name):
    with st.spinner("Reading image text..."):
        try:
            img = Image.open(uploaded_file).convert("RGB")
            big = img.resize((img.width*3, img.height*3), Image.LANCZOS)
            ocr = pytesseract.image_to_string(big, config=OCR_CONFIG).strip()
            thumb = img.copy(); thumb.thumbnail((300,300))
            buf = io.BytesIO(); thumb.save(buf, format="PNG")
            st.session_state.pending_image = {
                "name": uploaded_file.name,
                "thumb": buf.getvalue(),
                "ocr": ocr
            }
            st.success("Image uploaded — ready to send with your question")
        except:
            st.error("Could not read image.")
            st.session_state.pending_image = None

# Init chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role":"assistant","content":"Hello! How can I help you today?"}]

# DISPLAY CHAT
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user" and msg.get("image_thumb"):
            st.markdown(msg["user_text"])
            st.image(msg["image_thumb"], width=300)
        else:
            st.markdown(msg.get("user_text", msg["content"]))

# User input
prompt = st.chat_input("Type your question...")

if prompt:
    # Build clean payload for Ollama (only role + content)
    ocr_part = ""
    image_thumb = None

    if st.session_state.get("pending_image"):
        ocr = st.session_state.pending_image["ocr"]
        if ocr: ocr_part = f"uploaded-image-text{{{ocr}}}\n"
        image_thumb = st.session_state.pending_image["thumb"]
        st.session_state.pending_image = None

    full_internal = ocr_part + f"user-query{{{prompt}}}"

    # Save message with display info
    user_msg = {
        "role": "user",
        "content": full_internal,      # what Ollama sees
        "user_text": prompt            # what user sees
    }
    if image_thumb:
        user_msg["image_thumb"] = image_thumb

    st.session_state.messages.append(user_msg)

    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
        if image_thumb:
            st.image(image_thumb, width=300)

    # Send to AI
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        try:
            # Clean payload — ONLY role/content
            clean_history = [
                {"role": m["role"], "content": m["content"]} 
                for m in st.session_state.messages
            ]
            payload = {
                "model": current_model,
                "messages": clean_history,
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
                        token = json.loads(line).get("message",{}).get("content","")
                        full += token
                        placeholder.markdown(full + "▎")
                        time.sleep(0.008)
                placeholder.markdown(full)
        except Exception as e:
            placeholder.error("Connection failed — check Kaggle/ngrok is running.")

        st.session_state.messages.append({
            "role": "assistant",
            "content": full,
            "user_text": full
        })

st.markdown("<div class='footer'>Spartan AI • Senior Project • Dallin Geurts</div>", unsafe_allow_html=True)
