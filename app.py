# app.py — Spartan AI · Terminal-Luxury Redesign
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import warnings

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

from PIL import Image

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx as docx_module
except ImportError:
    docx_module = None

try:
    import pytesseract
    TESSERACT_OK = True
except ImportError:
    pytesseract = None
    TESSERACT_OK = False

# ── Config ────────────────────────────────────────────────────────────────────
NGROK_URL       = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME        = "dgeurts"
PASSWORD        = "thaidakar21"
OCR_CONFIG      = r"--oem 3 --psm 6"

MODEL_MAP = {
    "Assignment Generation": "spartan-generator",
    "Assignment Grader":     "spartan-grader",
    "AI Content Detector":   "spartan-detector",
    "Student Chatbot":       "spartan-student",
}

TOOL_META = {
    "Assignment Generation": {
        "tag":   "GEN",
        "desc":  "Generate custom assignments, rubrics, and prompts for any subject or grade.",
        "color": "#e2f0ff",
        "index": "01",
    },
    "Assignment Grader": {
        "tag":   "GRD",
        "desc":  "Upload student work and receive detailed rubric-aligned grading feedback.",
        "color": "#d4f7e7",
        "index": "02",
    },
    "AI Content Detector": {
        "tag":   "DET",
        "desc":  "Analyze submissions for AI-generated content and plagiarism signals.",
        "color": "#ffecd4",
        "index": "03",
    },
    "Student Chatbot": {
        "tag":   "STU",
        "desc":  "A responsible, curriculum-aware assistant to support student learning.",
        "color": "#ede8ff",
        "index": "04",
    },
}

st.set_page_config(page_title="Spartan AI", layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --bg:      #0a0a0b;
    --bg2:     #0f0f11;
    --bg3:     #161618;
    --line:    rgba(255,255,255,0.06);
    --line2:   rgba(255,255,255,0.10);
    --txt:     rgba(240,240,245,0.90);
    --txt2:    rgba(160,160,175,0.55);
    --txt3:    rgba(100,100,115,0.40);
    --accent:  #c8ff57;
    --r:       6px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
    background: var(--bg) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--txt) !important;
    -webkit-font-smoothing: antialiased !important;
}

.stApp {
    background-image:
        linear-gradient(var(--line) 1px, transparent 1px),
        linear-gradient(90deg, var(--line) 1px, transparent 1px) !important;
    background-size: 52px 52px !important;
}

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }

#MainMenu, footer, header,
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton { visibility: hidden !important; height: 0 !important; display: none !important; }

/* ─── SIDEBAR ─── */
section[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--line2) !important;
    box-shadow: none !important;
    min-width: 210px !important;
    max-width: 210px !important;
}
section[data-testid="stSidebar"] > div {
    padding: 0 !important;
    overflow: hidden !important;
    width: 210px !important;
}

.sb-brand {
    padding: 26px 18px 22px;
    border-bottom: 1px solid var(--line);
}
.sb-brand-row {
    display: flex; align-items: center; gap: 9px; margin-bottom: 4px;
}
.sb-sq {
    width: 26px; height: 26px; flex-shrink: 0;
    background: var(--accent); border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
}
.sb-sq svg { width: 12px; height: 12px; }
.sb-name {
    font-size: 0.9rem !important; font-weight: 600 !important;
    color: var(--txt) !important; letter-spacing: -0.01em;
    font-family: 'DM Sans', sans-serif !important;
}
.sb-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; color: var(--txt3);
    text-transform: uppercase; letter-spacing: 0.12em;
    padding-left: 35px;
}

.sb-section {
    font-family: 'DM Mono', monospace;
    font-size: 0.57rem; font-weight: 500;
    color: var(--txt3); text-transform: uppercase; letter-spacing: 0.16em;
    padding: 18px 18px 5px;
}

div[data-testid="stSidebar"] .stButton { padding: 0 8px !important; }
div[data-testid="stSidebar"] .stButton > button {
    all: unset !important;
    display: block !important;
    width: 100% !important;
    padding: 8px 10px !important;
    border-radius: var(--r) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.8rem !important; font-weight: 400 !important;
    color: var(--txt2) !important;
    cursor: pointer !important;
    transition: background 0.12s, color 0.12s !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    box-sizing: border-box !important;
    line-height: 1.4 !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg3) !important;
    color: var(--txt) !important;
}

.sb-foot {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 14px 18px;
    border-top: 1px solid var(--line);
    font-family: 'DM Mono', monospace;
    font-size: 0.57rem; color: var(--txt3); line-height: 1.9;
}

/* ─── MAIN ─── */
.main .block-container {
    max-width: 780px !important;
    padding: 0 2rem 7rem !important;
    position: relative; z-index: 2;
}

/* ─── HOME PAGE ─── */
.home-wrap { padding: 60px 0 44px; }
.home-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--accent);
    background: rgba(200,255,87,0.08);
    border: 1px solid rgba(200,255,87,0.18);
    border-radius: 3px; padding: 3px 10px;
    margin-bottom: 22px;
}
.home-h1 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 2.9rem !important; font-weight: 300 !important;
    line-height: 1.1 !important; letter-spacing: -0.04em !important;
    color: var(--txt) !important; margin-bottom: 8px !important;
}
.home-h1 b { font-weight: 600; color: #fff; }
.home-sub {
    font-size: 0.9rem; color: var(--txt2);
    line-height: 1.72; max-width: 420px;
    margin-bottom: 48px; font-weight: 300;
}

.tool-grid-border {
    border: 1px solid var(--line2);
    border-radius: 10px; overflow: hidden;
    margin-bottom: 44px;
}
.tool-grid { display: grid; grid-template-columns: 1fr 1fr; }

.tcard {
    background: var(--bg2);
    padding: 26px 24px;
    transition: background 0.18s;
}
.tcard:nth-child(1) { border-right: 1px solid var(--line2); border-bottom: 1px solid var(--line2); }
.tcard:nth-child(2) { border-bottom: 1px solid var(--line2); }
.tcard:nth-child(3) { border-right: 1px solid var(--line2); }
.tcard:hover { background: var(--bg3); }

.tcard-num {
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; color: var(--txt3); letter-spacing: 0.1em;
    margin-bottom: 14px;
}
.tcard-pill {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; font-weight: 500; letter-spacing: 0.1em;
    padding: 2px 7px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03);
    margin-bottom: 10px;
}
.tcard-name {
    font-size: 0.92rem; font-weight: 600;
    color: var(--txt); margin-bottom: 7px; letter-spacing: -0.01em;
}
.tcard-desc { font-size: 0.76rem; color: var(--txt2); line-height: 1.6; font-weight: 300; }

.home-foot-row {
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid var(--line); padding-top: 18px;
}
.home-foot-txt {
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; color: var(--txt3); letter-spacing: 0.08em;
}

/* hide invisible home nav buttons */
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton,
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton > button {
    display: none !important; height: 0 !important;
    padding: 0 !important; margin: 0 !important; border: none !important;
}

/* ─── TOOL TOP BAR ─── */
.topbar {
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 26px 0 18px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 22px;
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.topbar-pill {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; font-weight: 500; letter-spacing: 0.12em;
    padding: 3px 8px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.09);
    background: rgba(255,255,255,0.03);
    white-space: nowrap;
}
.topbar-title { font-size: 1.05rem; font-weight: 600; color: var(--txt); letter-spacing: -0.02em; }
.topbar-desc { font-size: 0.73rem; color: var(--txt2); font-weight: 300; margin-top: 2px; }

.nc-wrap .stButton > button {
    all: unset !important;
    display: inline-flex !important; align-items: center !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.63rem !important; letter-spacing: 0.08em !important;
    color: var(--txt3) !important;
    border: 1px solid var(--line2) !important;
    border-radius: var(--r) !important;
    padding: 6px 12px !important;
    cursor: pointer !important;
    transition: border-color 0.15s, color 0.15s, background 0.15s !important;
    white-space: nowrap !important;
}
.nc-wrap .stButton > button:hover {
    border-color: rgba(255,255,255,0.2) !important;
    color: var(--txt) !important;
    background: var(--bg3) !important;
}

/* ─── CHAT ─── */
.stChatMessage {
    background: transparent !important; border: none !important;
    padding: 3px 0 !important; gap: 12px !important;
}
div[data-testid="stChatMessageUser"] { flex-direction: row-reverse !important; }
div[data-testid="stChatMessageUser"] > div[data-testid="stChatMessageContent"] {
    background: var(--bg3) !important;
    border: 1px solid var(--line2) !important;
    border-radius: 8px 8px 2px 8px !important;
    padding: 10px 15px !important; max-width: 66% !important;
    font-size: 0.862rem !important; line-height: 1.65 !important;
    color: var(--txt) !important; box-shadow: none !important;
}
div[data-testid="stChatMessageAssistant"] > div[data-testid="stChatMessageContent"] {
    background: transparent !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px 8px 8px 2px !important;
    padding: 13px 17px !important; max-width: 80% !important;
    font-size: 0.862rem !important; line-height: 1.72 !important;
    color: rgba(215,220,235,0.88) !important; box-shadow: none !important;
}
div[data-testid="chatAvatarIcon-user"],
div[data-testid="chatAvatarIcon-assistant"] {
    background: var(--bg3) !important;
    border: 1px solid var(--line2) !important;
    border-radius: 5px !important; box-shadow: none !important;
}

/* ─── FILE UPLOADER ─── */
div[data-testid="stFileUploader"] > div {
    background: var(--bg2) !important;
    border: 1px dashed var(--line2) !important;
    border-radius: var(--r) !important;
    padding: 14px 18px !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stFileUploader"] > div:hover {
    border-color: rgba(200,255,87,0.22) !important;
}
div[data-testid="stFileUploader"] label,
div[data-testid="stFileUploader"] small {
    color: var(--txt2) !important;
    font-family: 'DM Sans', sans-serif !important; font-size: 0.78rem !important;
}

/* ─── CHAT INPUT ─── */
div[data-testid="stChatInput"] {
    background: var(--bg2) !important;
    border: 1px solid var(--line2) !important;
    border-radius: 8px !important; box-shadow: none !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stChatInput"]:focus-within {
    border-color: rgba(200,255,87,0.32) !important;
    box-shadow: 0 0 0 3px rgba(200,255,87,0.04) !important;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important; color: var(--txt) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.875rem !important; caret-color: var(--accent) !important;
}
div[data-testid="stChatInput"] textarea::placeholder { color: var(--txt3) !important; }
div[data-testid="stChatInput"] button {
    background: var(--accent) !important; border: none !important;
    border-radius: 5px !important; box-shadow: none !important;
}
div[data-testid="stChatInput"] button svg path { fill: #0a0a0b !important; }

/* ─── ALERTS ─── */
div[data-testid="stAlert"] {
    background: rgba(200,255,87,0.04) !important;
    border: 1px solid rgba(200,255,87,0.14) !important;
    border-radius: var(--r) !important;
    color: rgba(200,255,87,0.75) !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.72rem !important;
}

/* ─── THINKING ─── */
.thinking-row {
    display: inline-flex; align-items: center; gap: 9px; padding: 8px 0;
}
.t-dots { display: flex; gap: 4px; align-items: center; }
.t-dots span {
    display: block; width: 4px; height: 4px; border-radius: 50%;
    background: var(--accent);
    animation: tblink 1.1s ease-in-out infinite both;
}
.t-dots span:nth-child(2) { animation-delay: 0.18s; }
.t-dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes tblink {
    0%, 80%, 100% { opacity: 0.12; transform: scale(0.75); }
    40% { opacity: 1; transform: scale(1); }
}
.t-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.62rem; color: var(--txt3);
    text-transform: uppercase; letter-spacing: 0.14em;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [
    ("mode", "Home"), ("messages", []),
    ("pending_ocr_text", None), ("uploaded_file_name", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

def go_to_tool(name: str):
    st.session_state.mode            = name
    st.session_state.messages        = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
    st.session_state.pending_ocr_text   = None
    st.session_state.uploaded_file_name = None

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-brand-row">
            <div class="sb-sq">
                <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="1" y="1" width="4" height="4" fill="#0a0a0b"/>
                    <rect x="7" y="1" width="4" height="4" fill="#0a0a0b"/>
                    <rect x="1" y="7" width="4" height="4" fill="#0a0a0b"/>
                    <rect x="7" y="7" width="4" height="4" fill="#0a0a0b"/>
                </svg>
            </div>
            <span class="sb-name">Spartan AI</span>
        </div>
        <div class="sb-sub">Educational Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Home", key="sb_home"):
        st.session_state.mode            = "Home"
        st.session_state.messages        = []
        st.session_state.pending_ocr_text   = None
        st.session_state.uploaded_file_name = None
        st.rerun()

    st.markdown('<div class="sb-section">Tools</div>', unsafe_allow_html=True)

    for tool_name, meta in TOOL_META.items():
        if st.button(f"{meta['index']}  {tool_name}", key=f"sb_{tool_name}"):
            go_to_tool(tool_name)
            st.rerun()

    st.markdown("""
    <div class="sb-foot">
        Senior Project — 2025<br>
        Dallin Geurts
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Home":

    st.markdown("""
    <div class="home-wrap">
        <div class="home-badge">Senior Project &nbsp;·&nbsp; 2025</div>
        <h1 class="home-h1">The classroom,<br><b>intelligently assisted.</b></h1>
        <p class="home-sub">
            Four focused AI tools for educators and students — built for speed, transparency, and trust.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="tool-grid-border"><div class="tool-grid">', unsafe_allow_html=True)
    for name, meta in TOOL_META.items():
        st.markdown(f"""
        <div class="tcard">
            <div class="tcard-num">{meta['index']}</div>
            <div class="tcard-pill" style="color:{meta['color']};">{meta['tag']}</div>
            <div class="tcard-name">{name}</div>
            <div class="tcard-desc">{meta['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

    # invisible nav buttons (hidden by CSS)
    col1, col2 = st.columns(2)
    for idx, (name, _) in enumerate(TOOL_META.items()):
        with (col1 if idx % 2 == 0 else col2):
            if st.button(name, key=f"home_card_{name}"):
                go_to_tool(name)
                st.rerun()

    st.markdown("""
    <div class="home-foot-row">
        <div class="home-foot-txt">Spartan AI &nbsp;·&nbsp; Dallin Geurts &nbsp;·&nbsp; 2025</div>
        <div class="home-foot-txt">v1.0</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TOOL PAGE
# ══════════════════════════════════════════════════════════════════════════════
tool  = st.session_state.mode
model = MODEL_MAP[tool]
meta  = TOOL_META[tool]

col_hdr, col_btn = st.columns([5, 1])
with col_hdr:
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-left">
            <div class="topbar-pill" style="color:{meta['color']};">{meta['tag']}</div>
            <div>
                <div class="topbar-title">{tool}</div>
                <div class="topbar-desc">{meta['desc']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.markdown('<div class="nc-wrap" style="padding-top:26px; display:flex; justify-content:flex-end;">', unsafe_allow_html=True)
    if st.button("+ new chat", key="new_chat"):
        st.session_state.messages            = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
        st.session_state.pending_ocr_text    = None
        st.session_state.uploaded_file_name  = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg["content"]))

# ── File uploader ─────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "attach",
    type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "gif", "bmp", "tiff"],
    label_visibility="collapsed",
)

if uploaded_file is not None and uploaded_file.name != st.session_state.uploaded_file_name:
    with st.spinner("Reading…"):
        extracted = ""
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        try:
            if ext == "pdf":
                if PyPDF2:
                    reader = PyPDF2.PdfReader(uploaded_file)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: extracted += t + "\n"
                else:
                    extracted = "(PyPDF2 not installed)"
            elif ext == "docx":
                if docx_module:
                    d = docx_module.Document(uploaded_file)
                    for para in d.paragraphs: extracted += para.text + "\n"
                else:
                    extracted = "(python-docx not installed)"
            elif ext == "txt":
                extracted = uploaded_file.read().decode("utf-8", errors="ignore")
            elif ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]:
                if TESSERACT_OK:
                    img = Image.open(uploaded_file).convert("RGB")
                    extracted = pytesseract.image_to_string(img, config=OCR_CONFIG)
                else:
                    extracted = "(pytesseract not installed)"
            else:
                extracted = "(Unsupported file type)"

            extracted = extracted.strip() or "(No readable text found)"
            st.session_state.pending_ocr_text   = extracted
            st.session_state.uploaded_file_name = uploaded_file.name
            st.success(f"✓  {uploaded_file.name}")

        except Exception as e:
            st.error(f"Could not read file: {e}")

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Message Spartan AI…")

if user_input:
    ocr_text = st.session_state.pending_ocr_text
    if ocr_text:
        content = f"uploaded-file-text{{{ocr_text}}}\nuser-query{{{user_input}}}"
        st.session_state.pending_ocr_text   = None
        st.session_state.uploaded_file_name = None
    else:
        content = f"user-query{{{user_input}}}"

    st.session_state.messages.append({
        "role": "user", "content": content, "display_text": user_input,
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    full_response = ""

    with st.chat_message("assistant"):
        thinking_slot = st.empty()
        resp_slot     = st.empty()

        thinking_slot.markdown("""
        <div class="thinking-row">
            <div class="t-dots"><span></span><span></span><span></span></div>
            <div class="t-label">Processing</div>
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
                        resp_slot.markdown(full_response + "▌", unsafe_allow_html=True)
                        time.sleep(0.01)
                resp_slot.markdown(full_response)
                thinking_slot.empty()

        except Exception:
            thinking_slot.empty()
            full_response = ""
            resp_slot.markdown(
                "<span style='font-family:DM Mono,monospace;font-size:0.72rem;"
                "color:rgba(255,90,70,0.7);'>"
                "⚠  Server unreachable — please try again."
                "</span>",
                unsafe_allow_html=True,
            )

    if full_response:
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "display_text": full_response,
        })
