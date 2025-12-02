# app.py - Spartan AI Demo - Reworked Multi-Tool AI Interface with ANY FILE UPLOAD
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image
import PyPDF2
import docx
import io

# Config
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

# Page config
st.set_page_config(page_title="Spartan AI Demo", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    /* General background and text */
    body, .css-18e3th9 {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
    }
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22 !important;
        color: #c9d1d9 !important;
    }
    .css-1d391kg {
        color: #58a6ff !important;
    }
    /* Headings */
    h1, h2, h3 {
        color: #58a6ff !important;
    }
    /* File uploader */
    .stFileUploader > div {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        padding: 8px !important;
        color: #c9d1d9 !important;
    }
    /* Chat bubbles - user and assistant */
    .stChatMessage.user {
        background-color: #f85149 !important;
        border-radius: 12px !important;
        color: white !important;
    }
    .stChatMessage.assistant {
        background-color: #f0ad4e !important;
        border-radius: 12px !important;
        color: black !important;
    }
    /* Footer styling */
    footer {
        visibility: hidden;
        height: 40px;
    }
    .footer-text {
        text-align: center;
        color: #8b949e;
        font-size: 0.85em;
        padding: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "mode" not in st.session_state:
    st.session_state.mode = "Home"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_ocr_text" not in st.session_state:
    st.session_state.pending_ocr_text = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# Sidebar navigation
with st.sidebar:
    st.title("Spartan AI Demo")
    if st.button("Home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.session_state.pending_ocr_text = None
    st.markdown("**Tools**")
    for tool in MODEL_MAP.keys():
        if st.button(tool):
            st.session_state.mode = tool
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            }]
            st.session_state.pending_ocr_text = None
    st.markdown("---")
    st.caption("Senior Project by Dallin Geurts")

# Home page — centered with paragraph
if st.session_state.mode == "Home":
    st.markdown("<h1 style='text-align: center; color: #58a6ff;'>Spartan AI Demo</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; margin-bottom: 40px;'>Empowering Education with Responsible AI</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; max-width: 800px; margin: 0 auto; line-height: 1.7; font-size: 1.1rem;'>
        Spartan AI is a senior project designed to bring safe, powerful, and ethical AI tools directly into the classroom. 
        Teachers can generate assignments, grade submissions, and detect AI-generated content with confidence, while students can get real-time help through a responsible chatbot — and everything is built with transparency and academic integrity at its core.
        <br><br>
        This project demonstrates how local LLMs and OCR technology can be combined into a clean, student-friendly interface — all running privately and securely.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown('<div class="footer-text">Spartan AI • Senior Project • Dallin Geurts • 2025</div>', unsafe_allow_html=True)
    st.stop()

# Current AI tool
current_tool = st.session_state.mode
model = MODEL_MAP[current_tool]
st.title(current_tool)

# Display chat history
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg.get("display_text", msg["content"])
    with st.chat_message(role):
        st.markdown(content)

# FILE UPLOADER — NOW ACCEPTS ANY FILE
uploaded_file = st.file_uploader(
    "Upload a file (PDF, DOCX, TXT, images, etc.) — text will be extracted automatically",
    type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "gif", "bmp", "tiff"]
)

# Extract text from any supported file
if uploaded_file and uploaded_file.name != st.session_state.uploaded_file_name:
    with st.spinner("Extracting text from file..."):
        extracted_text = ""
        file_type = uploaded_file.name.split(".")[-1].lower()

        try:
            if file_type == "pdf":
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    extracted_text += page.extract_text() or ""
            elif file_type == "docx":
                doc = docx.Document(uploaded_file)
                for para in doc.paragraphs:
                    extracted_text += para.text + "\n"
            elif file_type == "txt":
                extracted_text = uploaded_file.read().decode("utf-8")
            elif file_type in ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]:
                img = Image.open(uploaded_file).convert("RGB")
                extracted_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
            else:
                extracted_text = "(Unsupported file type)"

            extracted_text = extracted_text.strip()
            if not extracted_text:
                extracted_text = "(No readable text found)"

            st.session_state.pending_ocr_text = extracted_text
            st.session_state.uploaded_file_name = uploaded_file.name
            st.success(f"File processed: {uploaded_file.name}")
        
        except Exception as e:
            st.error(f"Error reading file: {e}")
            st.session_state.pending_ocr_text = None

# User input
user_input = st.chat_input("Type your message here...")
if user_input:
    if st.session_state.pending_ocr_text:
        content = f"uploaded-file-text{{{st.session_state.pending_ocr_text}}}\nuser-query{{{user_input}}}"
        st.session_state.pending_ocr_text = None
    else:
        content = f"user-query{{{user_input}}}"

    st.session_state.messages.append({
        "role": "user",
        "content": content,
        "display_text": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        payload = {
            "model": model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            "stream": True
        }
        try:
            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600,
                verify=False,
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    token = json.loads(line).get("message", {}).get("content", "")
                    full_response += token
                    placeholder.markdown(full_response + " ")
                    time.sleep(0.01)
            placeholder.markdown(full_response)
        except Exception as e:
            placeholder.markdown(f"Error connecting to AI backend: {e}")

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "display_text": full_response
        })

# Footer
st.markdown('<div class="footer-text">Spartan AI • Senior Project • Dallin Geurts</div>', unsafe_allow_html=True)
