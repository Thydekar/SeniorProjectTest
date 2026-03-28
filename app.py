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
        "color": "#7dd3fc",
        "index": "01",
    },
    "Assignment Grader": {
        "tag":   "GRD",
        "desc":  "Upload student work and receive detailed rubric-aligned grading feedback.",
        "color": "#6ee7b7",
        "index": "02",
    },
    "AI Content Detector": {
        "tag":   "DET",
        "desc":  "Analyze submissions for AI-generated content and plagiarism signals.",
        "color": "#fbbf24",
        "index": "03",
    },
    "Student Chatbot": {
        "tag":   "STU",
        "desc":  "A responsible, curriculum-aware assistant to support student learning.",
        "color": "#c084fc",
        "index": "04",
    },
}

# ── Tag Parser ────────────────────────────────────────────────────────────────
OUTPUT_TEXT_RE = re.compile(r'\[output-text\](.*?)\[/output-text\]', re.DOTALL)
OUTPUT_FILE_RE = re.compile(
    r'\[output-file-(txt|md|pdf|docx)\](.*?)\[/output-file-(?:txt|md|pdf|docx)\]',
    re.DOTALL
)

def parse_ai_response(raw: str) -> list[dict]:
    segments = []
    cursor = 0
    all_matches = []
    for m in OUTPUT_TEXT_RE.finditer(raw):
        all_matches.append(("text", m))
    for m in OUTPUT_FILE_RE.finditer(raw):
        all_matches.append(("file", m))
    all_matches.sort(key=lambda x: x[1].start())
    for kind, m in all_matches:
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
    tail = raw[cursor:].strip()
    if tail:
        segments.append({"type": "text", "content": tail})
    return segments


def make_download_bytes(content: str, ext: str) -> tuple[bytes, str]:
    if ext in ("txt", "md"):
        return content.encode("utf-8"), "text/plain"
    if ext == "pdf":
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

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
    --bg:        #080809;
    --bg-panel:  rgba(14,14,18,0.82);
    --bg-card:   rgba(18,18,24,0.72);
    --bg-hover:  rgba(26,26,34,0.88);
    --border:    rgba(255,255,255,0.07);
    --border-hi: rgba(255,255,255,0.12);
    --txt:       rgba(232,232,242,0.93);
    --txt-2:     rgba(150,150,168,0.65);
    --txt-3:     rgba(85,85,100,0.50);
    --accent:    #c8ff57;
    --accent-bg: rgba(200,255,87,0.08);
    --accent-bd: rgba(200,255,87,0.20);
    --accent-glow: rgba(200,255,87,0.22);
    --r:         10px;
    --blur:      blur(20px);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
    background: var(--bg) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--txt) !important;
    -webkit-font-smoothing: antialiased !important;
}

/* Background: dark grid + radial spotlight */
.stApp {
    background:
        radial-gradient(ellipse 70% 40% at 60% 0%, rgba(200,255,87,0.035) 0%, transparent 65%),
        radial-gradient(ellipse 40% 30% at 10% 80%, rgba(120,100,255,0.025) 0%, transparent 60%),
        linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px),
        var(--bg) !important;
    background-size: 100%, 100%, 44px 44px, 44px 44px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(200,255,87,0.15); border-radius: 4px; }

/* Hide Streamlit chrome */
#MainMenu, footer, header,
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; }

/* ══════════════════════════════════════
   SIDEBAR
══════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: var(--bg-panel) !important;
    backdrop-filter: var(--blur) !important;
    -webkit-backdrop-filter: var(--blur) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 24px rgba(0,0,0,0.5) !important;
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

/* Brand */
.sb-brand {
    padding: 20px 14px 16px;
    border-bottom: 1px solid var(--border);
}
.sb-logo-row {
    display: flex; align-items: center; gap: 9px; margin-bottom: 3px;
}
.sb-logo {
    width: 28px; height: 28px;
    background: var(--accent);
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 0 0 1px rgba(200,255,87,0.3), 0 0 16px rgba(200,255,87,0.2);
}
.sb-logo svg { width: 14px; height: 14px; }
.sb-name {
    font-size: 0.875rem; font-weight: 600; letter-spacing: -0.02em;
    color: var(--txt);
}
.sb-tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5rem; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--txt-3); padding-left: 37px;
}

/* Section label */
.sb-section {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5rem; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--txt-3); padding: 16px 14px 5px;
}

/* Sidebar nav buttons */
div[data-testid="stSidebar"] .stButton {
    width: 100% !important;
    padding: 0 6px !important;
    margin: 0 !important;
}
div[data-testid="stSidebar"] .stButton > button {
    all: unset !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    padding: 7px 9px !important;
    margin: 1px 0 !important;
    border-radius: 7px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.77rem !important;
    font-weight: 400 !important;
    color: var(--txt-2) !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1 !important;
    transition: all 0.15s !important;
    box-sizing: border-box !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--accent-bg) !important;
    color: var(--txt) !important;
}

/* Sidebar footer */
.sb-foot {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 12px 14px;
    border-top: 1px solid var(--border);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5rem; color: var(--txt-3); line-height: 2;
    background: var(--bg-panel);
}
div[data-testid="stSidebar"] > div > div {
    padding-bottom: 60px !important;
}

/* ══════════════════════════════════════
   MAIN CONTENT
══════════════════════════════════════ */
.main .block-container {
    max-width: 820px !important;
    padding: 0 2.5rem 9rem !important;
}

/* ══════════════════════════════════════
   HOME PAGE
══════════════════════════════════════ */
.home-hero {
    padding: 64px 0 48px;
}
.home-eyebrow {
    display: inline-flex; align-items: center; gap: 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.575rem; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--accent);
    background: var(--accent-bg);
    border: 1px solid var(--accent-bd);
    border-radius: 5px; padding: 4px 10px;
    margin-bottom: 24px;
}
.home-eyebrow::before {
    content: '';
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
    flex-shrink: 0;
}
.home-title {
    font-size: 2.9rem; font-weight: 300; line-height: 1.08;
    letter-spacing: -0.045em; color: var(--txt);
    margin-bottom: 14px;
}
.home-title strong { font-weight: 700; color: #fff; }
.home-title .hi {
    font-weight: 700;
    background: linear-gradient(120deg, #c8ff57 0%, #a3e635 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.home-sub {
    font-size: 0.92rem; font-weight: 300;
    color: var(--txt-2); line-height: 1.75;
    max-width: 440px; margin-bottom: 52px;
}

/* Tool grid — all built as one HTML block */
.tgrid {
    display: grid; grid-template-columns: 1fr 1fr;
    border: 1px solid var(--border);
    border-radius: 14px; overflow: hidden;
    background: var(--bg-card);
    backdrop-filter: var(--blur);
    -webkit-backdrop-filter: var(--blur);
    box-shadow: 0 8px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
    margin-bottom: 48px;
}
.tc {
    padding: 26px 24px;
    transition: background 0.18s;
    position: relative;
}
.tc:nth-child(1),
.tc:nth-child(2) { border-bottom: 1px solid var(--border); }
.tc:nth-child(1),
.tc:nth-child(3) { border-right: 1px solid var(--border); }
.tc:hover { background: var(--bg-hover); }
.tc-idx {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.52rem; color: var(--txt-3);
    letter-spacing: 0.12em; margin-bottom: 14px;
}
.tc-tag {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.56rem; font-weight: 500; letter-spacing: 0.1em;
    padding: 2px 8px; border-radius: 4px;
    border: 1px solid currentColor;
    margin-bottom: 11px;
    opacity: 0.8;
}
.tc-name {
    font-size: 0.9rem; font-weight: 600;
    color: var(--txt); letter-spacing: -0.015em;
    margin-bottom: 7px;
}
.tc-desc {
    font-size: 0.73rem; color: var(--txt-2);
    line-height: 1.65; font-weight: 300;
}

/* Home footer */
.home-footer {
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid var(--border); padding-top: 18px;
}
.home-footer-txt {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.52rem; color: var(--txt-3); letter-spacing: 0.08em;
}

/* Hide invisible home nav buttons */
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton,
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton > button {
    display: none !important; height: 0 !important;
    padding: 0 !important; margin: 0 !important;
    overflow: hidden !important;
}

/* ══════════════════════════════════════
   TOOL TOPBAR
══════════════════════════════════════ */
.topbar {
    padding: 28px 0 18px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
    display: flex; align-items: center; gap: 14px;
    position: relative;
}
.topbar::after {
    content: '';
    position: absolute; bottom: -1px; left: 0;
    width: 60px; height: 1px;
    background: linear-gradient(90deg, var(--accent), transparent);
}
.tb-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.56rem; font-weight: 500; letter-spacing: 0.12em;
    padding: 4px 10px; border-radius: 5px;
    border: 1px solid currentColor;
    flex-shrink: 0;
}
.tb-info {}
.tb-title {
    font-size: 1rem; font-weight: 600;
    letter-spacing: -0.02em; color: var(--txt);
}
.tb-desc {
    font-size: 0.72rem; color: var(--txt-2);
    font-weight: 300; margin-top: 2px;
}

/* ══════════════════════════════════════
   CHAT MESSAGES
══════════════════════════════════════ */
.stChatMessage {
    background: transparent !important;
    border: none !important;
    padding: 5px 0 !important;
    gap: 10px !important;
}

/* Avatars — override default Streamlit colors */
div[data-testid="chatAvatarIcon-user"],
div[data-testid="chatAvatarIcon-assistant"] {
    width: 30px !important; height: 30px !important;
    border-radius: 8px !important;
    border: 1px solid var(--border-hi) !important;
    background: var(--bg-card) !important;
    backdrop-filter: var(--blur) !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
}
div[data-testid="chatAvatarIcon-user"] img,
div[data-testid="chatAvatarIcon-assistant"] img,
div[data-testid="chatAvatarIcon-user"] svg,
div[data-testid="chatAvatarIcon-assistant"] svg {
    filter: saturate(0) brightness(0.5) !important;
    width: 100% !important; height: 100% !important;
}
div[data-testid="chatAvatarIcon-user"] {
    border-color: var(--accent-bd) !important;
    background: var(--accent-bg) !important;
}

/* User message bubble */
div[data-testid="stChatMessageUser"] {
    flex-direction: row-reverse !important;
}
div[data-testid="stChatMessageUser"] > div[data-testid="stChatMessageContent"] {
    background: var(--accent-bg) !important;
    backdrop-filter: var(--blur) !important;
    -webkit-backdrop-filter: var(--blur) !important;
    border: 1px solid var(--accent-bd) !important;
    border-radius: 14px 14px 4px 14px !important;
    padding: 11px 16px !important;
    max-width: 70% !important;
    font-size: 0.87rem !important;
    line-height: 1.68 !important;
    color: var(--txt) !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2) !important;
}

/* Assistant message bubble */
div[data-testid="stChatMessageAssistant"] > div[data-testid="stChatMessageContent"] {
    background: var(--bg-card) !important;
    backdrop-filter: var(--blur) !important;
    -webkit-backdrop-filter: var(--blur) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px 14px 14px 14px !important;
    padding: 13px 18px !important;
    max-width: 86% !important;
    font-size: 0.87rem !important;
    line-height: 1.75 !important;
    color: rgba(218,222,240,0.92) !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15) !important;
}

/* ══════════════════════════════════════
   FILE DOWNLOAD CARD
══════════════════════════════════════ */
.fcard {
    background: var(--bg-card);
    backdrop-filter: var(--blur);
    border: 1px solid var(--accent-bd);
    border-radius: 12px;
    padding: 18px 20px;
    margin: 8px 0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
}
.fcard-hd {
    display: flex; align-items: center; gap: 12px; margin-bottom: 13px;
}
.fcard-icon {
    width: 36px; height: 36px; border-radius: 8px; flex-shrink: 0;
    background: var(--accent-bg); border: 1px solid var(--accent-bd);
    display: flex; align-items: center; justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem; font-weight: 500;
    color: var(--accent);
    box-shadow: 0 0 12px rgba(200,255,87,0.1);
}
.fcard-name {
    font-size: 0.84rem; font-weight: 600; color: var(--txt);
    letter-spacing: -0.01em;
}
.fcard-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.54rem; color: var(--txt-3); letter-spacing: 0.06em; margin-top: 2px;
}
.fcard-preview {
    background: rgba(6,6,9,0.6);
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 10px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem; color: var(--txt-2);
    line-height: 1.6; white-space: pre-wrap; word-break: break-word;
    max-height: 110px; overflow: hidden;
    margin-bottom: 14px;
    position: relative;
}
.fcard-preview::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 32px;
    background: linear-gradient(transparent, rgba(6,6,9,0.9));
    border-radius: 0 0 7px 7px;
}
.fcard .stDownloadButton > button {
    all: unset !important;
    display: inline-flex !important; align-items: center !important; gap: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.6rem !important; letter-spacing: 0.1em !important;
    color: #08080a !important;
    background: var(--accent) !important;
    border-radius: 7px !important;
    padding: 8px 16px !important; cursor: pointer !important;
    font-weight: 600 !important;
    box-shadow: 0 0 18px rgba(200,255,87,0.25) !important;
    transition: box-shadow 0.15s, opacity 0.15s !important;
}
.fcard .stDownloadButton > button:hover {
    box-shadow: 0 0 26px rgba(200,255,87,0.38) !important;
    opacity: 0.92 !important;
}

/* ══════════════════════════════════════
   FILE GENERATING CARD
══════════════════════════════════════ */
.fgen {
    background: var(--bg-card);
    backdrop-filter: var(--blur);
    border: 1px solid var(--accent-bd);
    border-radius: 12px;
    padding: 16px 18px;
    display: flex; align-items: center; gap: 14px;
    margin: 8px 0;
    box-shadow: 0 0 20px rgba(200,255,87,0.05);
}
.fgen-icon {
    width: 38px; height: 38px; border-radius: 8px; flex-shrink: 0;
    background: var(--accent-bg); border: 1px solid var(--accent-bd);
    display: flex; align-items: center; justify-content: center;
}
.fgen-icon svg { width: 16px; height: 16px; }
.fgen-title {
    font-size: 0.82rem; font-weight: 600; color: var(--txt);
    letter-spacing: -0.01em; margin-bottom: 4px;
}
.fgen-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.56rem; color: var(--accent); letter-spacing: 0.07em;
    display: flex; align-items: center; gap: 6px;
}
.fdots { display: flex; gap: 3px; align-items: center; }
.fdots span {
    display: block; width: 3px; height: 3px; border-radius: 50%;
    background: var(--accent);
    animation: blink 1.1s ease-in-out infinite both;
}
.fdots span:nth-child(2) { animation-delay: 0.18s; }
.fdots span:nth-child(3) { animation-delay: 0.36s; }

/* ══════════════════════════════════════
   THINKING INDICATOR
══════════════════════════════════════ */
.thinking {
    display: inline-flex; align-items: center; gap: 10px; padding: 8px 0;
}
.tdots { display: flex; gap: 4px; align-items: center; }
.tdots span {
    display: block; width: 5px; height: 5px; border-radius: 50%;
    background: var(--accent);
    animation: blink 1.1s ease-in-out infinite both;
}
.tdots span:nth-child(2) { animation-delay: 0.18s; }
.tdots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes blink {
    0%, 80%, 100% { opacity: 0.15; transform: scale(0.7); }
    40% { opacity: 1; transform: scale(1); }
}
.thinking-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem; color: var(--txt-3);
    text-transform: uppercase; letter-spacing: 0.18em;
}

/* ══════════════════════════════════════
   FILE UPLOADER (background)
══════════════════════════════════════ */
div[data-testid="stFileUploader"] > div {
    background: var(--bg-card) !important;
    backdrop-filter: var(--blur) !important;
    border: 1px dashed var(--border-hi) !important;
    border-radius: var(--r) !important;
    padding: 10px 14px !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stFileUploader"] > div:hover {
    border-color: var(--accent-bd) !important;
}
div[data-testid="stFileUploader"] label,
div[data-testid="stFileUploader"] small {
    color: var(--txt-2) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.77rem !important;
}

/* ══════════════════════════════════════
   CHAT INPUT — glass bar
══════════════════════════════════════ */
div[data-testid="stChatInput"] {
    background: var(--bg-card) !important;
    backdrop-filter: var(--blur) !important;
    -webkit-backdrop-filter: var(--blur) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 28px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03) !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stChatInput"]:focus-within {
    border-color: rgba(200,255,87,0.28) !important;
    box-shadow: 0 4px 28px rgba(0,0,0,0.3), 0 0 0 3px rgba(200,255,87,0.05) !important;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--txt) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    caret-color: var(--accent) !important;
}
div[data-testid="stChatInput"] textarea::placeholder {
    color: var(--txt-3) !important;
}
/* Send button */
div[data-testid="stChatInput"] button {
    background: var(--accent) !important;
    border: none !important;
    border-radius: 8px !important;
    width: 32px !important; height: 32px !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    box-shadow: 0 0 12px rgba(200,255,87,0.2) !important;
    transition: box-shadow 0.15s !important;
    flex-shrink: 0 !important;
    margin: auto 4px auto 0 !important;
}
div[data-testid="stChatInput"] button:hover {
    box-shadow: 0 0 20px rgba(200,255,87,0.35) !important;
}
div[data-testid="stChatInput"] button svg {
    width: 14px !important; height: 14px !important;
}
div[data-testid="stChatInput"] button svg path,
div[data-testid="stChatInput"] button svg rect {
    fill: #06060a !important;
    stroke: none !important;
}

/* ══════════════════════════════════════
   BOTTOM BAR — icon buttons
══════════════════════════════════════ */
/* All horizontal blocks align at bottom */
div[data-testid="stHorizontalBlock"] {
    align-items: flex-end !important;
    gap: 6px !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(1),
div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
    flex: 0 0 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    padding: 0 !important;
}

/* ══════════════════════════════════════
   ALERTS
══════════════════════════════════════ */
div[data-testid="stAlert"] {
    background: var(--accent-bg) !important;
    border: 1px solid var(--accent-bd) !important;
    border-radius: var(--r) !important;
    color: rgba(200,255,87,0.75) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.7rem !important;
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

# ── Render assistant message ──────────────────────────────────────────────────
def render_assistant_message(raw: str, msg_index: int):
    segments = parse_ai_response(raw)
    if not segments:
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
            st.markdown(f"""
<div class="fcard">
  <div class="fcard-hd">
    <div class="fcard-icon">{icon_label}</div>
    <div>
      <div class="fcard-name">{fname}</div>
      <div class="fcard-meta">{size_kb} KB &middot; ready to download</div>
    </div>
  </div>
  <div class="fcard-preview">{preview}</div>
</div>
""", unsafe_allow_html=True)
            file_bytes, mime = make_download_bytes(content, ext)
            st.download_button(
                label=f"↓  Download {fname}",
                data=file_bytes,
                file_name=fname,
                mime=mime,
                key=f"dl_{msg_index}_{seg_i}_{ext}",
            )

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="sb-brand">
  <div class="sb-logo-row">
    <div class="sb-logo">
      <svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M7 2L12 7L7 12L2 7L7 2Z" fill="#08080a"/>
        <circle cx="7" cy="7" r="2" fill="#08080a" opacity="0.6"/>
      </svg>
    </div>
    <span class="sb-name">Spartan AI</span>
  </div>
  <div class="sb-tagline">Educational Intelligence</div>
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
  Senior Project · 2025<br>Dallin Geurts
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Home":

    # Build all four tool cards as one HTML string so the CSS grid works
    cards_html = ""
    for name, tmeta in TOOL_META.items():
        cards_html += f"""
<div class="tc">
  <div class="tc-idx">{tmeta['index']}</div>
  <div class="tc-tag" style="color:{tmeta['color']};">{tmeta['tag']}</div>
  <div class="tc-name">{name}</div>
  <div class="tc-desc">{tmeta['desc']}</div>
</div>"""

    st.markdown(f"""
<div class="home-hero">
  <div class="home-eyebrow">Senior Project &nbsp;·&nbsp; 2025</div>
  <div class="home-title">The classroom,<br><strong>intelligently</strong> <span class="hi">assisted.</span></div>
  <div class="home-sub">Four focused AI tools for educators and students — built for speed, transparency, and trust.</div>
</div>
<div class="tgrid">{cards_html}</div>
<div class="home-footer">
  <div class="home-footer-txt">Spartan AI · Dallin Geurts · 2025</div>
  <div class="home-footer-txt">v1.0</div>
</div>
""", unsafe_allow_html=True)

    # Hidden nav buttons (CSS hides them; kept so rerun can fire)
    col1, col2 = st.columns(2)
    for idx, (name, _) in enumerate(TOOL_META.items()):
        with (col1 if idx % 2 == 0 else col2):
            if st.button(name, key=f"home_card_{name}"):
                go_to_tool(name)
                st.rerun()

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TOOL PAGE
# ══════════════════════════════════════════════════════════════════════════════
tool  = st.session_state.mode
model = MODEL_MAP[tool]
tmeta = TOOL_META[tool]

st.markdown(f"""
<div class="topbar">
  <div class="tb-tag" style="color:{tmeta['color']}; border-color:{tmeta['color']}50;">{tmeta['tag']}</div>
  <div class="tb-info">
    <div class="tb-title">{tool}</div>
    <div class="tb-desc">{tmeta['desc']}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant":
            render_assistant_message(msg["content"], i)
        else:
            st.markdown(msg.get("display_text", msg["content"]))

# ── Bottom bar: [new chat] [file] [chat input] ────────────────────────────────
bot_nc, bot_file, bot_chat = st.columns([1, 1, 14])

with bot_nc:
    st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button {
    all: unset !important;
    width: 40px !important; height: 40px !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    background: var(--bg-card) !important;
    backdrop-filter: var(--blur) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 10px !important;
    cursor: pointer !important;
    font-size: 1rem !important;
    color: var(--txt-3) !important;
    transition: all 0.15s !important;
    box-sizing: border-box !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button:hover {
    background: var(--accent-bg) !important;
    border-color: var(--accent-bd) !important;
    color: var(--accent) !important;
    box-shadow: 0 0 12px rgba(200,255,87,0.1) !important;
}
</style>
""", unsafe_allow_html=True)
    if st.button("↺", key="new_chat", help="New chat"):
        go_to_tool(tool)
        st.rerun()

with bot_file:
    st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] {
    width: 40px !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div {
    background: var(--bg-card) !important;
    backdrop-filter: var(--blur) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 10px !important;
    padding: 0 !important;
    width: 40px !important; height: 40px !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    overflow: hidden !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div:hover {
    background: var(--accent-bg) !important;
    border-color: var(--accent-bd) !important;
    box-shadow: 0 0 12px rgba(200,255,87,0.1) !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] label,
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] small,
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] p {
    display: none !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] button {
    all: unset !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    width: 40px !important; height: 40px !important;
    cursor: pointer !important;
    font-size: 1.05rem !important;
    color: var(--txt-3) !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div:hover button {
    color: var(--accent) !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
    position: absolute !important;
    width: 7px !important; height: 7px !important;
    background: var(--accent) !important;
    border-radius: 50% !important;
    top: 4px !important; right: 4px !important;
    overflow: hidden !important;
    font-size: 0 !important;
    box-shadow: 0 0 6px var(--accent) !important;
}
</style>
""", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "📎",
        type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "gif", "bmp", "tiff"],
        label_visibility="collapsed",
        key="file_uploader",
    )

with bot_chat:
    user_input = st.chat_input("Message Spartan AI…")

# ── Process uploaded file ─────────────────────────────────────────────────────
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
            st.toast(f"✓  {uploaded_file.name}", icon="📎")
        except Exception as e:
            st.error(f"Could not read file: {e}")

# ── Handle user input ─────────────────────────────────────────────────────────
if user_input:
    ocr_text = st.session_state.pending_ocr_text
    if ocr_text:
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
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    full_response = ""

    with st.chat_message("assistant", avatar="🤖"):
        thinking_slot = st.empty()
        resp_slot     = st.empty()

        thinking_slot.markdown("""
<div class="thinking">
  <div class="tdots"><span></span><span></span><span></span></div>
  <div class="thinking-label">Processing</div>
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

            ANY_OPEN_RE  = re.compile(r'\[(output-text|output-file-(?:txt|md|pdf|docx))\]')
            FILE_OPEN_RE = re.compile(r'\[output-file-(?:txt|md|pdf|docx)\]')

            FILE_GEN_HTML = """
<div class="fgen">
  <div class="fgen-icon">
    <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 2h7l4 4v9H3V2z" stroke="#c8ff57" stroke-width="1.2" stroke-linejoin="round"/>
      <path d="M10 2v4h4" stroke="#c8ff57" stroke-width="1.2" stroke-linejoin="round"/>
      <path d="M5 9h6M5 11.5h4" stroke="#c8ff57" stroke-width="1" stroke-linecap="round"/>
    </svg>
  </div>
  <div>
    <div class="fgen-title">Generating file…</div>
    <div class="fgen-sub">
      Writing your assignment
      <div class="fdots"><span></span><span></span><span></span></div>
    </div>
  </div>
</div>
"""

            stream_state = "waiting"
            gen_slot     = None
            active_slot  = resp_slot

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

                    if stream_state == "waiting":
                        thinking_slot.empty()
                        m = ANY_OPEN_RE.search(full_response)
                        if m:
                            tag_name = m.group(1)
                            if tag_name == "output-text":
                                stream_state = "text"
                                inner_so_far = full_response[m.end():]
                                live = re.sub(r'\[/output-text\].*', '', inner_so_far).strip()
                                if live:
                                    active_slot.markdown(live + "▌", unsafe_allow_html=True)
                            else:
                                stream_state = "file"
                                pre = full_response[:m.start()]
                                pre_text = OUTPUT_TEXT_RE.sub(r'\1', pre).strip()
                                if pre_text:
                                    active_slot.markdown(pre_text)
                                gen_slot = st.empty()
                                gen_slot.markdown(FILE_GEN_HTML, unsafe_allow_html=True)

                    elif stream_state == "text":
                        m = re.search(r'\[output-text\](.*?)(?=\[/output-text\]|\[output-file-)', full_response, re.DOTALL)
                        if m:
                            live = m.group(1).strip()
                        else:
                            start = full_response.rfind('[output-text]')
                            live  = full_response[start + len('[output-text]'):].strip()
                            live  = re.sub(r'\[/?$|\[/output', '', live)
                        active_slot.markdown(live + "▌", unsafe_allow_html=True)

                        if FILE_OPEN_RE.search(full_response):
                            stream_state = "file"
                            active_slot.markdown(live)
                            gen_slot = st.empty()
                            gen_slot.markdown(FILE_GEN_HTML, unsafe_allow_html=True)

                    time.sleep(0.01)

                thinking_slot.empty()
                resp_slot.empty()
                if gen_slot:
                    gen_slot.empty()
                render_assistant_message(full_response, len(st.session_state.messages))

        except Exception:
            thinking_slot.empty()
            full_response = ""
            resp_slot.markdown(
                "<span style='font-family:JetBrains Mono,monospace;font-size:0.7rem;"
                "color:rgba(255,85,65,0.75);letter-spacing:0.04em;'>"
                "⚠ &nbsp;Server unreachable — please try again."
                "</span>",
                unsafe_allow_html=True,
            )

    if full_response:
        st.session_state.messages.append({
            "role":         "assistant",
            "content":      full_response,
            "display_text": full_response,
        })
