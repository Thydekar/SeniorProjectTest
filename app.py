# app.py — Spartan AI
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import re
import io
import warnings
import base64

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

# ── Tag Parser ────────────────────────────────────────────────────────────────
# Supported output tags from the AI
OUTPUT_TEXT_RE = re.compile(r'\[output-text\](.*?)\[/output-text\]', re.DOTALL)
OUTPUT_FILE_RE = re.compile(
    r'\[output-file-(txt|md|pdf|docx)\](.*?)\[/output-file-(?:txt|md|pdf|docx)\]',
    re.DOTALL
)

def parse_ai_response(raw: str) -> list[dict]:
    """
    Parse a raw AI response into a list of segments.
    Each segment is either:
      {"type": "text",  "content": str}
      {"type": "file",  "ext": str, "content": str}
    Untagged text (shouldn't happen per spec, but handle gracefully) is wrapped
    as a text segment so nothing is silently swallowed.
    """
    segments = []
    cursor = 0

    # Find all tagged regions in document order
    all_matches = []
    for m in OUTPUT_TEXT_RE.finditer(raw):
        all_matches.append(("text", m))
    for m in OUTPUT_FILE_RE.finditer(raw):
        all_matches.append(("file", m))

    # Sort by start position
    all_matches.sort(key=lambda x: x[1].start())

    for kind, m in all_matches:
        # Any gap before this match → treat as plain text (fallback)
        gap = raw[cursor:m.start()].strip()
        if gap:
            segments.append({"type": "text", "content": gap})

        if kind == "text":
            content = m.group(1).strip()
            if content:
                segments.append({"type": "text", "content": content})
        else:
            ext     = m.group(1).lower()
            content = m.group(2).strip()
            if content:
                segments.append({"type": "file", "ext": ext, "content": content})

        cursor = m.end()

    # Trailing untagged text
    tail = raw[cursor:].strip()
    if tail:
        segments.append({"type": "text", "content": tail})

    return segments


def make_download_bytes(content: str, ext: str) -> tuple[bytes, str]:
    """Return (bytes, mime_type) for a file download."""
    if ext in ("txt", "md"):
        return content.encode("utf-8"), "text/plain"
    if ext == "pdf":
        # We don't have reportlab etc., so deliver as plain text with .pdf name
        return content.encode("utf-8"), "text/plain"
    if ext == "docx":
        if docx_module:
            doc = docx_module.Document()
            for line in content.split("\n"):
                doc.add_paragraph(line)
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            return buf.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            return content.encode("utf-8"), "text/plain"
    return content.encode("utf-8"), "text/plain"


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Spartan AI", layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --bg:      #0a0a0b;
    --bg2:     #0f0f11;
    --bg3:     #161618;
    --bg4:     #1c1c1f;
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

::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }

#MainMenu, footer, header,
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; }

/* ════════════════════════════════
   SIDEBAR
════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: var(--bg2) !important;
    border-right: 1px solid var(--line2) !important;
    box-shadow: none !important;
    width: 200px !important;
    min-width: 200px !important;
    max-width: 200px !important;
}
section[data-testid="stSidebar"] > div {
    padding: 0 !important;
    width: 200px !important;
    min-width: 200px !important;
    max-width: 200px !important;
    overflow-x: hidden !important;
}

/* brand block */
.sb-brand {
    padding: 24px 16px 18px;
    border-bottom: 1px solid var(--line);
}
.sb-brand-row { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.sb-sq {
    width: 24px; height: 24px; flex-shrink: 0;
    background: var(--accent); border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
}
.sb-sq svg { width: 11px; height: 11px; }
.sb-name {
    font-size: 0.85rem; font-weight: 600;
    color: var(--txt); letter-spacing: -0.01em;
    white-space: nowrap;
}
.sb-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.55rem; color: var(--txt3);
    text-transform: uppercase; letter-spacing: 0.12em;
    padding-left: 32px; white-space: nowrap;
}

/* section label */
.sb-section {
    font-family: 'DM Mono', monospace;
    font-size: 0.54rem; font-weight: 500;
    color: var(--txt3); text-transform: uppercase; letter-spacing: 0.16em;
    padding: 16px 16px 4px;
}

/* nav buttons — unset all Streamlit default styles */
div[data-testid="stSidebar"] .stButton {
    width: 100% !important;
    padding: 0 6px !important;
    margin: 0 !important;
}
div[data-testid="stSidebar"] .stButton > button {
    all: unset !important;
    display: block !important;
    width: 100% !important;
    padding: 7px 10px !important;
    margin: 1px 0 !important;
    border-radius: 5px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 400 !important;
    color: var(--txt2) !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.3 !important;
    transition: background 0.12s ease, color 0.12s ease !important;
    box-sizing: border-box !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg3) !important;
    color: var(--txt) !important;
}

.sb-foot {
    padding: 12px 16px 16px;
    border-top: 1px solid var(--line);
    font-family: 'DM Mono', monospace;
    font-size: 0.54rem; color: var(--txt3); line-height: 1.9;
}
/* add bottom breathing room above footer so last button never overlaps */
div[data-testid="stSidebar"] .stButton {
    margin-bottom: 0 !important;
}
div[data-testid="stSidebar"] > div > div {
    padding-bottom: 70px !important;
}

/* ════════════════════════════════
   MAIN
════════════════════════════════ */
.main .block-container {
    max-width: 780px !important;
    padding: 0 2rem 7rem !important;
    position: relative; z-index: 2;
}

/* ════════════════════════════════
   HOME
════════════════════════════════ */
.home-wrap { padding: 56px 0 40px; }
.home-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--accent);
    background: rgba(200,255,87,0.07);
    border: 1px solid rgba(200,255,87,0.18);
    border-radius: 3px; padding: 3px 9px; margin-bottom: 20px;
}
.home-h1 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 2.8rem !important; font-weight: 300 !important;
    line-height: 1.1 !important; letter-spacing: -0.04em !important;
    color: var(--txt) !important; margin-bottom: 10px !important;
}
.home-h1 b { font-weight: 600; color: #fff; }
.home-sub {
    font-size: 0.88rem; color: var(--txt2);
    line-height: 1.72; max-width: 400px;
    margin-bottom: 44px; font-weight: 300;
}
.tool-grid-border {
    border: 1px solid var(--line2); border-radius: 10px;
    overflow: hidden; margin-bottom: 40px;
}
.tool-grid { display: grid; grid-template-columns: 1fr 1fr; }
.tcard {
    background: var(--bg2); padding: 24px 22px;
    transition: background 0.18s;
}
.tcard:nth-child(1) { border-right: 1px solid var(--line2); border-bottom: 1px solid var(--line2); }
.tcard:nth-child(2) { border-bottom: 1px solid var(--line2); }
.tcard:nth-child(3) { border-right: 1px solid var(--line2); }
.tcard:hover { background: var(--bg3); }
.tcard-num {
    font-family: 'DM Mono', monospace;
    font-size: 0.56rem; color: var(--txt3); letter-spacing: 0.1em; margin-bottom: 12px;
}
.tcard-pill {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; font-weight: 500; letter-spacing: 0.1em;
    padding: 2px 7px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03); margin-bottom: 9px;
}
.tcard-name {
    font-size: 0.9rem; font-weight: 600;
    color: var(--txt); margin-bottom: 6px; letter-spacing: -0.01em;
}
.tcard-desc { font-size: 0.74rem; color: var(--txt2); line-height: 1.6; font-weight: 300; }
.home-foot-row {
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid var(--line); padding-top: 16px;
}
.home-foot-txt {
    font-family: 'DM Mono', monospace;
    font-size: 0.56rem; color: var(--txt3); letter-spacing: 0.08em;
}

/* hide invisible home nav buttons */
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton,
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton > button {
    display: none !important; height: 0 !important;
    padding: 0 !important; margin: 0 !important;
}

/* ════════════════════════════════
   TOOL TOPBAR
════════════════════════════════ */
.topbar {
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 24px 0 16px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 20px;
}
.topbar-left { display: flex; align-items: center; gap: 11px; }
.topbar-pill {
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; font-weight: 500; letter-spacing: 0.12em;
    padding: 3px 8px; border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.09);
    background: rgba(255,255,255,0.03); white-space: nowrap; flex-shrink: 0;
}
.topbar-title { font-size: 1rem; font-weight: 600; color: var(--txt); letter-spacing: -0.02em; }
.topbar-desc { font-size: 0.72rem; color: var(--txt2); font-weight: 300; margin-top: 2px; }

/* new chat button */
.nc-wrap .stButton > button {
    all: unset !important;
    display: inline-flex !important; align-items: center !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.61rem !important; letter-spacing: 0.08em !important;
    color: var(--txt3) !important;
    border: 1px solid var(--line2) !important;
    border-radius: var(--r) !important;
    padding: 6px 11px !important; cursor: pointer !important;
    transition: all 0.15s !important; white-space: nowrap !important;
}
.nc-wrap .stButton > button:hover {
    border-color: rgba(255,255,255,0.2) !important;
    color: var(--txt) !important; background: var(--bg3) !important;
}

/* ════════════════════════════════
   CHAT MESSAGES
════════════════════════════════ */
.stChatMessage {
    background: transparent !important; border: none !important;
    padding: 3px 0 !important; gap: 12px !important;
}
div[data-testid="stChatMessageUser"] { flex-direction: row-reverse !important; }
div[data-testid="stChatMessageUser"] > div[data-testid="stChatMessageContent"] {
    background: var(--bg3) !important;
    border: 1px solid var(--line2) !important;
    border-radius: 8px 8px 2px 8px !important;
    padding: 10px 14px !important; max-width: 66% !important;
    font-size: 0.855rem !important; line-height: 1.65 !important;
    color: var(--txt) !important; box-shadow: none !important;
}
div[data-testid="stChatMessageAssistant"] > div[data-testid="stChatMessageContent"] {
    background: transparent !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px 8px 8px 2px !important;
    padding: 12px 16px !important; max-width: 82% !important;
    font-size: 0.855rem !important; line-height: 1.72 !important;
    color: rgba(215,220,235,0.88) !important; box-shadow: none !important;
}
div[data-testid="chatAvatarIcon-user"],
div[data-testid="chatAvatarIcon-assistant"] {
    background: var(--bg3) !important;
    border: 1px solid var(--line2) !important;
    border-radius: 5px !important; box-shadow: none !important;
}

/* ════════════════════════════════
   FILE DOWNLOAD CARD
════════════════════════════════ */
.file-card {
    background: var(--bg2);
    border: 1px solid var(--line2);
    border-radius: 8px;
    padding: 16px 18px;
    margin: 6px 0;
}
.file-card-header {
    display: flex; align-items: center; gap: 10px; margin-bottom: 12px;
}
.file-card-icon {
    width: 30px; height: 30px; border-radius: 5px;
    background: rgba(200,255,87,0.08);
    border: 1px solid rgba(200,255,87,0.18);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; color: var(--accent); flex-shrink: 0;
    font-family: 'DM Mono', monospace; font-weight: 500; letter-spacing: 0.05em;
}
.file-card-meta { flex: 1; min-width: 0; }
.file-card-name {
    font-size: 0.82rem; font-weight: 600; color: var(--txt);
    letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.file-card-size {
    font-family: 'DM Mono', monospace;
    font-size: 0.57rem; color: var(--txt3); letter-spacing: 0.06em; margin-top: 1px;
}
.file-card-preview {
    background: var(--bg3);
    border: 1px solid var(--line);
    border-radius: 5px;
    padding: 10px 12px;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem; color: var(--txt2);
    line-height: 1.6; white-space: pre-wrap; word-break: break-word;
    max-height: 120px; overflow: hidden;
    margin-bottom: 12px;
    position: relative;
}
.file-card-preview::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 32px;
    background: linear-gradient(transparent, var(--bg3));
    border-radius: 0 0 5px 5px;
}

/* streamlit download button inside card */
.file-card .stDownloadButton > button {
    all: unset !important;
    display: inline-flex !important; align-items: center !important; gap: 6px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.63rem !important; letter-spacing: 0.08em !important;
    color: #0a0a0b !important;
    background: var(--accent) !important;
    border-radius: 5px !important;
    padding: 7px 14px !important; cursor: pointer !important;
    font-weight: 500 !important;
    transition: opacity 0.15s !important;
}
.file-card .stDownloadButton > button:hover { opacity: 0.85 !important; }

/* ════════════════════════════════
   FILE GENERATING CARD (streaming)
════════════════════════════════ */
.file-gen-card {
    background: var(--bg2);
    border: 1px solid rgba(200,255,87,0.18);
    border-radius: 8px;
    padding: 14px 16px;
    display: flex; align-items: center; gap: 12px;
    margin: 6px 0;
}
.file-gen-icon {
    width: 32px; height: 32px; border-radius: 5px; flex-shrink: 0;
    background: rgba(200,255,87,0.08);
    border: 1px solid rgba(200,255,87,0.2);
    display: flex; align-items: center; justify-content: center;
}
.file-gen-icon svg { width: 14px; height: 14px; }
.file-gen-text { flex: 1; }
.file-gen-title {
    font-size: 0.8rem; font-weight: 600; color: var(--txt);
    letter-spacing: -0.01em; margin-bottom: 3px;
}
.file-gen-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; color: var(--accent); letter-spacing: 0.06em;
}
.file-gen-dots { display: flex; gap: 3px; align-items: center; }
.file-gen-dots span {
    display: block; width: 3px; height: 3px; border-radius: 50%;
    background: var(--accent);
    animation: tblink 1.1s ease-in-out infinite both;
}
.file-gen-dots span:nth-child(2) { animation-delay: 0.18s; }
.file-gen-dots span:nth-child(3) { animation-delay: 0.36s; }

/* ════════════════════════════════
   FILE UPLOADER
════════════════════════════════ */
div[data-testid="stFileUploader"] > div {
    background: var(--bg2) !important;
    border: 1px dashed var(--line2) !important;
    border-radius: var(--r) !important;
    padding: 12px 16px !important;
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

/* ════════════════════════════════
   CHAT INPUT
════════════════════════════════ */
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

/* ════════════════════════════════
   ALERTS
════════════════════════════════ */
div[data-testid="stAlert"] {
    background: rgba(200,255,87,0.04) !important;
    border: 1px solid rgba(200,255,87,0.14) !important;
    border-radius: var(--r) !important;
    color: rgba(200,255,87,0.75) !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.72rem !important;
}

/* ════════════════════════════════
   THINKING INDICATOR
════════════════════════════════ */
.thinking-row {
    display: inline-flex; align-items: center; gap: 9px; padding: 6px 0;
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
    font-size: 0.6rem; color: var(--txt3);
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
    st.session_state.mode               = name
    st.session_state.messages           = [{"role": "assistant", "content": "[output-text]Hello! How can I help you today?[/output-text]"}]
    st.session_state.pending_ocr_text   = None
    st.session_state.uploaded_file_name = None

# ── Render a single assistant message (parsed) ────────────────────────────────
def render_assistant_message(raw: str, msg_index: int):
    """Parse and render an assistant response with text bubbles + file cards."""
    segments = parse_ai_response(raw)

    if not segments:
        # fallback: just show raw
        st.markdown(raw)
        return

    for seg_i, seg in enumerate(segments):
        if seg["type"] == "text":
            st.markdown(seg["content"])

        elif seg["type"] == "file":
            ext     = seg["ext"]
            content = seg["content"]
            fname   = f"Spartan-Assignment.{ext}"
            preview = content[:400]
            size_kb = round(len(content.encode("utf-8")) / 1024, 1)

            ext_labels = {"txt": "TXT", "md": "MD", "pdf": "PDF", "docx": "DOCX"}
            icon_label = ext_labels.get(ext, ext.upper())

            # Card header
            st.markdown(f"""
            <div class="file-card">
                <div class="file-card-header">
                    <div class="file-card-icon">{icon_label}</div>
                    <div class="file-card-meta">
                        <div class="file-card-name">{fname}</div>
                        <div class="file-card-size">{size_kb} KB &nbsp;·&nbsp; ready to download</div>
                    </div>
                </div>
                <div class="file-card-preview">{preview}</div>
            </div>
            """, unsafe_allow_html=True)

            # Download button (outside the HTML card so Streamlit can render it)
            file_bytes, mime = make_download_bytes(content, ext)
            dl_key = f"dl_{msg_index}_{seg_i}_{ext}"
            st.download_button(
                label=f"↓  Download  {fname}",
                data=file_bytes,
                file_name=fname,
                mime=mime,
                key=dl_key,
            )


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-brand-row">
            <div class="sb-sq">
                <svg viewBox="0 0 11 11" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="1" y="1" width="3.5" height="3.5" fill="#0a0a0b"/>
                    <rect x="6.5" y="1" width="3.5" height="3.5" fill="#0a0a0b"/>
                    <rect x="1" y="6.5" width="3.5" height="3.5" fill="#0a0a0b"/>
                    <rect x="6.5" y="6.5" width="3.5" height="3.5" fill="#0a0a0b"/>
                </svg>
            </div>
            <span class="sb-name">Spartan AI</span>
        </div>
        <div class="sb-sub">Educational Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Home", key="sb_home"):
        st.session_state.mode               = "Home"
        st.session_state.messages           = []
        st.session_state.pending_ocr_text   = None
        st.session_state.uploaded_file_name = None
        st.rerun()

    st.markdown('<div class="sb-section">Tools</div>', unsafe_allow_html=True)

    for tool_name, tmeta in TOOL_META.items():
        label = f"{tmeta['index']}  {tool_name}"
        if st.button(label, key=f"sb_{tool_name}"):
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
            Four focused AI tools for educators and students —
            built for speed, transparency, and trust.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="tool-grid-border"><div class="tool-grid">', unsafe_allow_html=True)
    for name, tmeta in TOOL_META.items():
        st.markdown(f"""
        <div class="tcard">
            <div class="tcard-num">{tmeta['index']}</div>
            <div class="tcard-pill" style="color:{tmeta['color']};">{tmeta['tag']}</div>
            <div class="tcard-name">{name}</div>
            <div class="tcard-desc">{tmeta['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

    # hidden nav buttons (CSS kills them; kept so rerun can fire)
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
tmeta = TOOL_META[tool]

col_hdr, col_btn = st.columns([5, 1])
with col_hdr:
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-left">
            <div class="topbar-pill" style="color:{tmeta['color']};">{tmeta['tag']}</div>
            <div>
                <div class="topbar-title">{tool}</div>
                <div class="topbar-desc">{tmeta['desc']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.markdown('<div class="nc-wrap" style="padding-top:24px; display:flex; justify-content:flex-end;">', unsafe_allow_html=True)
    if st.button("+ new chat", key="new_chat"):
        go_to_tool(tool)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_assistant_message(msg["content"], i)
        else:
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
    # Build content sent to the model
    ocr_text = st.session_state.pending_ocr_text
    if ocr_text:
        # Use the spec format for image/file input
        api_content = f"[input-image-text]{ocr_text}[/input-image-text]\n[output-text]{user_input}[/output-text]"
        st.session_state.pending_ocr_text   = None
        st.session_state.uploaded_file_name = None
    else:
        api_content = f"[output-text]{user_input}[/output-text]"

    st.session_state.messages.append({
        "role":         "user",
        "content":      api_content,
        "display_text": user_input,
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    # ── Stream assistant response ─────────────────────────────────────────────
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

            # Detects ANY opening output tag as soon as it fully arrives
            ANY_OPEN_RE  = re.compile(r'\[(output-text|output-file-(?:txt|md|pdf|docx))\]')
            FILE_OPEN_RE = re.compile(r'\[output-file-(?:txt|md|pdf|docx)\]')

            FILE_GEN_HTML = """
            <div class="file-gen-card">
                <div class="file-gen-icon">
                    <svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M2 1h7l3 3v9H2V1z" stroke="#c8ff57" stroke-width="1" stroke-linejoin="round"/>
                        <path d="M9 1v3h3" stroke="#c8ff57" stroke-width="1" stroke-linejoin="round"/>
                        <path d="M4 7h6M4 9.5h4" stroke="#c8ff57" stroke-width="0.9" stroke-linecap="round"/>
                    </svg>
                </div>
                <div class="file-gen-text">
                    <div class="file-gen-title">Generating file…</div>
                    <div class="file-gen-sub" style="display:flex;align-items:center;gap:6px;">
                        Spartan AI is writing your assignment
                        <div class="file-gen-dots"><span></span><span></span><span></span></div>
                    </div>
                </div>
            </div>
            """

            # ── streaming state machine ──────────────────────────────────────
            # States:
            #   "waiting"     — no tag seen yet, sitting on thinking indicator
            #   "text"        — inside [output-text], streaming chars live
            #   "file"        — inside [output-file-*], showing generating card
            stream_state  = "waiting"
            gen_slot      = None   # placeholder for file-gen card
            active_slot   = resp_slot  # current text slot to write into

            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600,
                verify=False,
                stream=True,
            ) as r:
                r.raise_for_status()

                for line in r.iter_lines():
                    if not line:
                        continue
                    token = json.loads(line).get("message", {}).get("content", "")
                    full_response += token

                    # ── dismiss thinking indicator on first token ────────────
                    if stream_state == "waiting":
                        thinking_slot.empty()
                        # Check whether a complete opening tag has arrived yet
                        m = ANY_OPEN_RE.search(full_response)
                        if m:
                            tag_name = m.group(1)  # e.g. "output-text" or "output-file-md"
                            if tag_name == "output-text":
                                stream_state = "text"
                                # Show whatever text content has arrived so far
                                inner_so_far = full_response[m.end():]
                                # Strip any partial/complete closing tag from live view
                                live = re.sub(r'\[/output-text\].*', '', inner_so_far).strip()
                                if live:
                                    active_slot.markdown(live + "▌", unsafe_allow_html=True)
                            else:
                                # It's a file tag
                                stream_state = "file"
                                # If any [output-text] blocks came before, render them
                                pre = full_response[:m.start()]
                                pre_text = OUTPUT_TEXT_RE.sub(r'\1', pre).strip()
                                if pre_text:
                                    active_slot.markdown(pre_text)
                                gen_slot = st.empty()
                                gen_slot.markdown(FILE_GEN_HTML, unsafe_allow_html=True)

                    elif stream_state == "text":
                        # Extract the growing inner content of the current [output-text] block
                        m = re.search(r'\[output-text\](.*?)(?=\[/output-text\]|\[output-file-)', full_response, re.DOTALL)
                        if m:
                            live = m.group(1).strip()
                        else:
                            # Tag not fully closed yet — show everything after the opening tag
                            start = full_response.rfind('[output-text]')
                            live  = full_response[start + len('[output-text]'):].strip()
                            # Hide partial closing tag chars that are mid-arrival
                            live  = re.sub(r'\[/?$|\[/output', '', live)

                        active_slot.markdown(live + "▌", unsafe_allow_html=True)

                        # Did a file tag open after this text block?
                        if FILE_OPEN_RE.search(full_response):
                            stream_state = "file"
                            active_slot.markdown(live)   # finalise text without cursor
                            gen_slot = st.empty()
                            gen_slot.markdown(FILE_GEN_HTML, unsafe_allow_html=True)

                    # state == "file": just accumulate, card stays up
                    time.sleep(0.01)

                # ── stream finished — full parse render ──────────────────────
                thinking_slot.empty()
                resp_slot.empty()
                if gen_slot:
                    gen_slot.empty()
                render_assistant_message(full_response, len(st.session_state.messages))

        except Exception:
            thinking_slot.empty()
            full_response = ""
            resp_slot.markdown(
                "<span style='font-family:DM Mono,monospace;font-size:0.7rem;"
                "color:rgba(255,90,70,0.7);'>"
                "⚠  Server unreachable — please try again."
                "</span>",
                unsafe_allow_html=True,
            )

    if full_response:
        st.session_state.messages.append({
            "role":         "assistant",
            "content":      full_response,
            "display_text": full_response,
        })
