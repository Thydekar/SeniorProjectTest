# app.py - Spartan AI Demo — Redesigned Professional UI
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    import docx
except ImportError:
    docx = None

# ── Config ──────────────────────────────────────────────────────────────────
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"
MODEL_MAP = {
    "Assignment Generation": "spartan-generator",
    "Assignment Grader":     "spartan-grader",
    "AI Content Detector":   "spartan-detector",
    "Student Chatbot":       "spartan-student",
}
TOOL_META = {
    "Assignment Generation": {
        "icon": "✦",
        "desc": "Generate custom assignments, rubrics, and prompts for any subject or grade level.",
        "color": "#4f8ef7",
    },
    "Assignment Grader": {
        "icon": "◈",
        "desc": "Upload student work and receive detailed, rubric-aligned grading feedback.",
        "color": "#34d399",
    },
    "AI Content Detector": {
        "icon": "◉",
        "desc": "Analyze submissions for AI-generated content and plagiarism signals.",
        "color": "#f97316",
    },
    "Student Chatbot": {
        "icon": "◎",
        "desc": "A responsible, curriculum-aware assistant to support student learning.",
        "color": "#a78bfa",
    },
}
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
OCR_CONFIG = r"--oem 3 --psm 6"

st.set_page_config(page_title="Spartan AI", layout="wide", initial_sidebar_state="expanded")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #080c14 !important;
    color: #d4ddf0 !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d1220 !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }

.sidebar-logo {
    padding: 28px 24px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 16px;
}
.sidebar-logo h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.35rem;
    color: #e8edf8 !important;
    letter-spacing: -0.02em;
    margin: 0 0 4px !important;
}
.sidebar-logo p {
    font-size: 0.7rem;
    color: #4a5568;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.sidebar-section-label {
    font-size: 0.65rem;
    font-weight: 600;
    color: #3a4560;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 0 24px 8px;
    margin-top: 4px;
}

/* ── Nav Buttons ── */
.stButton > button {
    background: transparent !important;
    border: none !important;
    color: #7b8db0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 400 !important;
    padding: 10px 20px !important;
    width: 100% !important;
    text-align: left !important;
    border-radius: 0 !important;
    transition: all 0.15s ease !important;
    display: block !important;
    cursor: pointer !important;
}
.stButton > button:hover {
    background: rgba(79, 142, 247, 0.08) !important;
    color: #d4ddf0 !important;
    border-left: 2px solid #4f8ef7 !important;
    padding-left: 18px !important;
}
.stButton > button:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* Home button styling */
div[data-testid="stSidebar"] .stButton:first-of-type > button {
    font-weight: 500 !important;
    color: #9aacc8 !important;
}

/* New Chat button — top of main area */
.new-chat-wrapper .stButton > button {
    background: rgba(79,142,247,0.12) !important;
    border: 1px solid rgba(79,142,247,0.25) !important;
    color: #4f8ef7 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    padding: 7px 16px !important;
    border-radius: 6px !important;
    width: auto !important;
    letter-spacing: 0.01em;
}
.new-chat-wrapper .stButton > button:hover {
    background: rgba(79,142,247,0.22) !important;
    border-left: 1px solid rgba(79,142,247,0.25) !important;
    padding-left: 16px !important;
    color: #7fb3ff !important;
}

/* ── Main area ── */
.main .block-container {
    max-width: 860px !important;
    padding: 2rem 2rem 6rem !important;
}

/* ── Tool Page Header ── */
.tool-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 28px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.tool-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    flex-shrink: 0;
}
.tool-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1.5rem;
    color: #e8edf8 !important;
    margin: 0;
    letter-spacing: -0.02em;
}

/* ── Chat Messages ── */
.stChatMessage {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
}
.stChatMessage[data-testid="stChatMessageUser"] {
    flex-direction: row-reverse !important;
}
.stChatMessage[data-testid="stChatMessageUser"] .stMarkdown {
    background: #1a2540 !important;
    border: 1px solid rgba(79,142,247,0.2) !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 12px 16px !important;
    color: #c8d8f0 !important;
    font-size: 0.9rem !important;
    line-height: 1.6 !important;
    max-width: 75% !important;
}
.stChatMessage[data-testid="stChatMessageAssistant"] .stMarkdown {
    background: #111827 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 14px 18px !important;
    color: #c8d8f0 !important;
    font-size: 0.9rem !important;
    line-height: 1.7 !important;
    max-width: 82% !important;
}

/* Avatar icons */
.stChatMessage [data-testid="chatAvatarIcon-user"],
.stChatMessage [data-testid="chatAvatarIcon-assistant"] {
    background: #1a2540 !important;
    border-radius: 8px !important;
    border: 1px solid rgba(79,142,247,0.15) !important;
}

/* ── File Uploader ── */
.stFileUploader {
    margin: 16px 0 8px !important;
}
.stFileUploader > div {
    background: #0d1220 !important;
    border: 1px dashed rgba(79,142,247,0.25) !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    transition: border-color 0.2s ease;
}
.stFileUploader > div:hover {
    border-color: rgba(79,142,247,0.5) !important;
}
.stFileUploader label {
    color: #7b8db0 !important;
    font-size: 0.82rem !important;
}

/* ── Chat Input ── */
.stChatInputContainer {
    background: #0d1220 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
}
.stChatInputContainer:focus-within {
    border-color: rgba(79,142,247,0.4) !important;
    box-shadow: 0 0 0 3px rgba(79,142,247,0.06) !important;
}
.stChatInputContainer textarea {
    background: transparent !important;
    color: #d4ddf0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
}
.stChatInputContainer textarea::placeholder { color: #3a4a68 !important; }

/* ── Success / Error / Spinner ── */
.stSuccess {
    background: rgba(52,211,153,0.08) !important;
    border: 1px solid rgba(52,211,153,0.2) !important;
    border-radius: 8px !important;
    color: #34d399 !important;
    font-size: 0.82rem !important;
}
.stAlert { border-radius: 8px !important; }

/* ── Home Cards ── */
.home-hero {
    text-align: center;
    padding: 60px 0 48px;
}
.home-hero h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 3rem;
    color: #e8edf8 !important;
    letter-spacing: -0.04em;
    margin-bottom: 16px;
    line-height: 1.1;
}
.home-hero h1 span {
    background: linear-gradient(135deg, #4f8ef7 0%, #7ba7ff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.home-hero p {
    color: #5a6a88;
    font-size: 1.05rem;
    max-width: 560px;
    margin: 0 auto 40px;
    line-height: 1.7;
}

.tool-card {
    background: #0d1220;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 24px;
    transition: border-color 0.2s, transform 0.2s;
    cursor: pointer;
    height: 100%;
}
.tool-card:hover {
    border-color: rgba(79,142,247,0.3);
    transform: translateY(-2px);
}
.tool-card-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    margin-bottom: 14px;
}
.tool-card h3 {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    color: #e8edf8 !important;
    margin: 0 0 8px !important;
    letter-spacing: -0.01em;
}
.tool-card p {
    color: #5a6a88;
    font-size: 0.82rem;
    line-height: 1.55;
    margin: 0;
}

.home-footer {
    text-align: center;
    padding: 40px 0 0;
    color: #2a3550;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    border-top: 1px solid rgba(255,255,255,0.04);
    margin-top: 48px;
}

/* ── Thinking animation ── */
.thinking-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 14px 18px;
    background: #111827;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px 16px 16px 4px;
    width: fit-content;
}
.thinking-wrap span {
    font-size: 0.78rem;
    color: #4a5a78;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.thinking-dots { display: flex; gap: 4px; }
.thinking-dots b {
    width: 5px; height: 5px;
    background: #4f8ef7;
    border-radius: 50%;
    display: inline-block;
    animation: pulse 1.2s infinite both;
}
.thinking-dots b:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots b:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse {
    0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; height: 0; }
.css-1rs6os { visibility: visible; }
div[data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if "mode"               not in st.session_state: st.session_state.mode               = "Home"
if "messages"           not in st.session_state: st.session_state.messages           = []
if "pending_ocr_text"   not in st.session_state: st.session_state.pending_ocr_text   = None
if "uploaded_file_name" not in st.session_state: st.session_state.uploaded_file_name = None

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h1>Spartan AI</h1>
        <p>Educational Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⌂  Home", key="home_btn"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.session_state.pending_ocr_text = None
        st.rerun()

    st.markdown('<div class="sidebar-section-label">Tools</div>', unsafe_allow_html=True)

    for tool in MODEL_MAP.keys():
        meta = TOOL_META[tool]
        label = f"{meta['icon']}  {tool}"
        if st.button(label, key=f"nav_{tool}"):
            st.session_state.mode = tool
            st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
            st.session_state.pending_ocr_text = None
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='padding: 16px 24px; border-top: 1px solid rgba(255,255,255,0.04); margin-top: auto;'>
        <p style='font-size: 0.72rem; color: #2a3550; margin: 0; line-height: 1.6;'>
            Senior Project<br>
            <span style='color: #3a4a68;'>Dallin Geurts · 2025</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ── Home Page ────────────────────────────────────────────────────────────────
if st.session_state.mode == "Home":
    st.markdown("""
    <div class="home-hero">
        <h1>Education, <span>Augmented</span></h1>
        <p>
            Safe, powerful AI tools built for the classroom — from assignment generation
            to academic integrity checks, all running privately and responsibly.
        </p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2, gap="medium")
    tools = list(TOOL_META.items())
    for i, (name, meta) in enumerate(tools):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="tool-card">
                <div class="tool-card-icon" style="background: {meta['color']}18; color: {meta['color']};">
                    {meta['icon']}
                </div>
                <h3>{name}</h3>
                <p>{meta['desc']}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div class="home-footer">
        Spartan AI &nbsp;·&nbsp; Senior Project &nbsp;·&nbsp; Dallin Geurts &nbsp;·&nbsp; 2025
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Tool Page ────────────────────────────────────────────────────────────────
current_tool = st.session_state.mode
model        = MODEL_MAP[current_tool]
meta         = TOOL_META[current_tool]

# Header row: icon + title + new chat button
hcol1, hcol2 = st.columns([6, 1])
with hcol1:
    st.markdown(f"""
    <div class="tool-header">
        <div class="tool-icon" style="background: {meta['color']}18; color: {meta['color']};">
            {meta['icon']}
        </div>
        <p class="tool-title">{current_tool}</p>
    </div>
    """, unsafe_allow_html=True)
with hcol2:
    st.markdown('<div class="new-chat-wrapper">', unsafe_allow_html=True)
    if st.button("+ New chat", key="new_chat_btn"):
        st.session_state.messages           = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
        st.session_state.pending_ocr_text   = None
        st.session_state.uploaded_file_name = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Chat history ─────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg["content"]))

# ── File uploader ─────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Attach a file — PDF, DOCX, TXT, or image (OCR supported)",
    type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "gif", "bmp", "tiff"],
    label_visibility="visible",
)

if uploaded_file and uploaded_file.name != st.session_state.uploaded_file_name:
    with st.spinner("Reading file…"):
        extracted_text = ""
        file_type = uploaded_file.name.rsplit(".", 1)[-1].lower()
        try:
            if file_type == "pdf" and PyPDF2:
                reader = PyPDF2.PdfReader(uploaded_file)
                for page in reader.pages:
                    t = page.extract_text()
                    if t: extracted_text += t + "\n"
            elif file_type == "docx" and docx:
                doc = docx.Document(uploaded_file)
                for para in doc.paragraphs:
                    extracted_text += para.text + "\n"
            elif file_type == "txt":
                extracted_text = uploaded_file.read().decode("utf-8", errors="ignore")
            elif file_type in ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]:
                img = Image.open(uploaded_file).convert("RGB")
                extracted_text = pytesseract.image_to_string(img, config=OCR_CONFIG)
            else:
                extracted_text = "(Unsupported file type)"

            extracted_text = extracted_text.strip() or "(No readable text found)"
            st.session_state.pending_ocr_text   = extracted_text
            st.session_state.uploaded_file_name = uploaded_file.name
            st.success(f"✓  {uploaded_file.name} processed successfully")
        except Exception as e:
            st.error(f"Could not read file: {e}")
            st.session_state.pending_ocr_text = None

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Message Spartan AI…")

if user_input:
    if st.session_state.pending_ocr_text:
        content = f"uploaded-file-text{{{st.session_state.pending_ocr_text}}}\nuser-query{{{user_input}}}"
        st.session_state.pending_ocr_text = None
    else:
        content = f"user-query{{{user_input}}}"

    st.session_state.messages.append({
        "role": "user", "content": content, "display_text": user_input
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    # ── AI response ──────────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        thinking_slot  = st.empty()
        response_slot  = st.empty()
        full_response  = ""

        thinking_slot.markdown("""
        <div class="thinking-wrap">
            <span>Thinking</span>
            <div class="thinking-dots"><b></b><b></b><b></b></div>
        </div>
        """, unsafe_allow_html=True)

        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                "stream": True,
            }
            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600,
                verify=False,
                stream=True,
            ) as r:
                r.raise_for_status()
                first_token = True
                for line in r.iter_lines():
                    if line:
                        token = json.loads(line).get("message", {}).get("content", "")
                        full_response += token
                        if first_token:
                            thinking_slot.empty()
                            first_token = False
                        response_slot.markdown(full_response + "▋", unsafe_allow_html=True)
                        time.sleep(0.01)
                response_slot.markdown(full_response)
                thinking_slot.empty()

        except Exception:
            thinking_slot.empty()
            response_slot.markdown(
                "<span style='color:#f97316; font-size:0.85rem;'>"
                "⚠ Could not reach the server. Please try again."
                "</span>",
                unsafe_allow_html=True,
            )

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "display_text": full_response,
    })
