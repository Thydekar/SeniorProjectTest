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

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --bg:      #07070a;
    --bg2:     #0d0d10;
    --bg3:     #141418;
    --bg4:     #1a1a1f;
    --line:    rgba(255,255,255,0.05);
    --line2:   rgba(255,255,255,0.09);
    --txt:     rgba(235,235,245,0.92);
    --txt2:    rgba(155,155,175,0.60);
    --txt3:    rgba(90,90,110,0.50);
    --accent:  #c8ff57;
    --accent2: rgba(200,255,87,0.12);
    --accent3: rgba(200,255,87,0.05);
    --glow:    rgba(200,255,87,0.18);
    --glow2:   rgba(200,255,87,0.06);
    --r:       8px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
    background: var(--bg) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--txt) !important;
    -webkit-font-smoothing: antialiased !important;
}

/* Subtle grid + radial spotlight */
.stApp {
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -10%, rgba(200,255,87,0.04) 0%, transparent 70%),
        linear-gradient(var(--line) 1px, transparent 1px),
        linear-gradient(90deg, var(--line) 1px, transparent 1px) !important;
    background-size: 100% 100%, 48px 48px, 48px 48px !important;
}

::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(200,255,87,0.12); border-radius: 3px; }

#MainMenu, footer, header,
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; }

/* ════════════════════════════════
   SIDEBAR — GLASS
════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: rgba(10,10,14,0.75) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border-right: 1px solid rgba(200,255,87,0.07) !important;
    box-shadow: 4px 0 32px rgba(0,0,0,0.4) !important;
    width: 210px !important;
    min-width: 210px !important;
    max-width: 210px !important;
}
section[data-testid="stSidebar"] > div {
    padding: 0 !important;
    width: 210px !important;
    min-width: 210px !important;
    max-width: 210px !important;
    overflow-x: hidden !important;
}

/* brand block */
.sb-brand {
    padding: 24px 16px 18px;
    border-bottom: 1px solid var(--line);
    position: relative;
}
.sb-brand::after {
    content: '';
    position: absolute;
    bottom: 0; left: 16px; right: 16px; height: 1px;
    background: linear-gradient(90deg, transparent, var(--glow), transparent);
}
.sb-brand-row { display: flex; align-items: center; gap: 9px; margin-bottom: 4px; }

/* logo square with glow */
.sb-sq {
    width: 26px; height: 26px; flex-shrink: 0;
    background: var(--accent);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 10px var(--glow), 0 0 24px rgba(200,255,87,0.08);
}
.sb-sq svg { width: 12px; height: 12px; }
.sb-name {
    font-size: 0.88rem; font-weight: 600;
    color: var(--txt); letter-spacing: -0.02em;
    white-space: nowrap;
}
.sb-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.54rem; color: var(--txt3);
    text-transform: uppercase; letter-spacing: 0.14em;
    padding-left: 35px; white-space: nowrap;
}

/* section label */
.sb-section {
    font-family: 'DM Mono', monospace;
    font-size: 0.52rem; font-weight: 500;
    color: var(--txt3); text-transform: uppercase; letter-spacing: 0.18em;
    padding: 18px 16px 5px;
}

/* nav buttons */
div[data-testid="stSidebar"] .stButton {
    width: 100% !important;
    padding: 0 8px !important;
    margin: 0 !important;
}
div[data-testid="stSidebar"] .stButton > button {
    all: unset !important;
    display: block !important;
    width: 100% !important;
    padding: 7px 10px !important;
    margin: 1px 0 !important;
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 400 !important;
    color: var(--txt2) !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.3 !important;
    transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease !important;
    box-sizing: border-box !important;
    border: 1px solid transparent !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(200,255,87,0.06) !important;
    border-color: rgba(200,255,87,0.1) !important;
    color: var(--txt) !important;
    box-shadow: 0 0 12px rgba(200,255,87,0.04) !important;
}

.sb-foot {
    padding: 12px 16px 16px;
    border-top: 1px solid var(--line);
    font-family: 'DM Mono', monospace;
    font-size: 0.53rem; color: var(--txt3); line-height: 2;
}
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
    max-width: 800px !important;
    padding: 0 2rem 8rem !important;
    position: relative; z-index: 2;
}

/* ════════════════════════════════
   HOME
════════════════════════════════ */
.home-wrap { padding: 60px 0 44px; }
.home-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--accent);
    background: rgba(200,255,87,0.06);
    border: 1px solid rgba(200,255,87,0.2);
    border-radius: 4px; padding: 4px 10px; margin-bottom: 22px;
    box-shadow: 0 0 14px rgba(200,255,87,0.07);
}
.home-badge::before {
    content: '';
    display: inline-block; width: 5px; height: 5px;
    background: var(--accent); border-radius: 50%;
    box-shadow: 0 0 6px var(--accent);
}
.home-h1 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 3rem !important; font-weight: 300 !important;
    line-height: 1.08 !important; letter-spacing: -0.04em !important;
    color: var(--txt) !important; margin-bottom: 12px !important;
}
.home-h1 b { font-weight: 700; color: #fff; }
.home-h1 .glow-word {
    background: linear-gradient(135deg, #c8ff57, #90ef2a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.home-sub {
    font-size: 0.9rem; color: var(--txt2);
    line-height: 1.75; max-width: 420px;
    margin-bottom: 48px; font-weight: 300;
}

/* Tool grid — glass cards */
.tool-grid-border {
    border: 1px solid rgba(200,255,87,0.08);
    border-radius: 14px;
    overflow: hidden; margin-bottom: 44px;
    box-shadow: 0 0 40px rgba(0,0,0,0.3), 0 0 1px rgba(200,255,87,0.06) inset;
    backdrop-filter: blur(8px);
}
.tool-grid { display: grid; grid-template-columns: 1fr 1fr; }
.tcard {
    background: rgba(13,13,16,0.6);
    padding: 26px 24px;
    transition: background 0.2s, box-shadow 0.2s;
    position: relative;
}
.tcard:nth-child(1) { border-right: 1px solid rgba(255,255,255,0.06); border-bottom: 1px solid rgba(255,255,255,0.06); }
.tcard:nth-child(2) { border-bottom: 1px solid rgba(255,255,255,0.06); }
.tcard:nth-child(3) { border-right: 1px solid rgba(255,255,255,0.06); }
.tcard:hover {
    background: rgba(20,20,24,0.85);
    box-shadow: inset 0 0 60px rgba(200,255,87,0.02);
}
.tcard-num {
    font-family: 'DM Mono', monospace;
    font-size: 0.55rem; color: var(--txt3); letter-spacing: 0.12em; margin-bottom: 13px;
}
.tcard-pill {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; font-weight: 500; letter-spacing: 0.1em;
    padding: 2px 8px; border-radius: 4px;
    border: 1px solid currentColor;
    opacity: 0.75;
    background: rgba(255,255,255,0.02); margin-bottom: 10px;
}
.tcard-name {
    font-size: 0.92rem; font-weight: 600;
    color: var(--txt); margin-bottom: 6px; letter-spacing: -0.015em;
}
.tcard-desc { font-size: 0.74rem; color: var(--txt2); line-height: 1.65; font-weight: 300; }
.home-foot-row {
    display: flex; align-items: center; justify-content: space-between;
    border-top: 1px solid var(--line); padding-top: 18px;
}
.home-foot-txt {
    font-family: 'DM Mono', monospace;
    font-size: 0.55rem; color: var(--txt3); letter-spacing: 0.08em;
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
    padding: 28px 0 18px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 22px;
    position: relative;
}
.topbar::after {
    content: '';
    position: absolute; bottom: -1px; left: 0; width: 80px; height: 1px;
    background: linear-gradient(90deg, var(--accent), transparent);
    opacity: 0.5;
}
.topbar-left { display: flex; align-items: center; gap: 13px; }
.topbar-pill {
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem; font-weight: 500; letter-spacing: 0.12em;
    padding: 4px 10px; border-radius: 5px;
    border: 1px solid currentColor;
    opacity: 0.8;
    background: rgba(255,255,255,0.02); white-space: nowrap; flex-shrink: 0;
    box-shadow: 0 0 12px rgba(0,0,0,0.2);
}
.topbar-title { font-size: 1.05rem; font-weight: 600; color: var(--txt); letter-spacing: -0.025em; }
.topbar-desc { font-size: 0.72rem; color: var(--txt2); font-weight: 300; margin-top: 2px; }

/* bottom bar alignment */
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

/* ════════════════════════════════
   CHAT MESSAGES — GLASS
════════════════════════════════ */
.stChatMessage {
    background: transparent !important; border: none !important;
    padding: 4px 0 !important; gap: 12px !important;
}

/* User bubble */
div[data-testid="stChatMessageUser"] { flex-direction: row-reverse !important; }
div[data-testid="stChatMessageUser"] > div[data-testid="stChatMessageContent"] {
    background: rgba(200,255,87,0.06) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(200,255,87,0.14) !important;
    border-radius: 12px 12px 3px 12px !important;
    padding: 11px 16px !important; max-width: 68% !important;
    font-size: 0.865rem !important; line-height: 1.68 !important;
    color: var(--txt) !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.25), 0 0 1px rgba(200,255,87,0.08) inset !important;
}

/* Assistant bubble */
div[data-testid="stChatMessageAssistant"] > div[data-testid="stChatMessageContent"] {
    background: rgba(13,13,16,0.55) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px 12px 12px 3px !important;
    padding: 13px 18px !important; max-width: 84% !important;
    font-size: 0.865rem !important; line-height: 1.75 !important;
    color: rgba(220,225,240,0.90) !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.2) !important;
}

/* Avatars */
div[data-testid="chatAvatarIcon-user"] {
    background: rgba(200,255,87,0.08) !important;
    border: 1px solid rgba(200,255,87,0.18) !important;
    border-radius: 7px !important;
    box-shadow: 0 0 10px rgba(200,255,87,0.06) !important;
}
div[data-testid="chatAvatarIcon-assistant"] {
    background: rgba(20,20,26,0.8) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 7px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
}

/* ════════════════════════════════
   FILE DOWNLOAD CARD — GLASS
════════════════════════════════ */
.file-card {
    background: rgba(13,13,16,0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(200,255,87,0.12);
    border-radius: 12px;
    padding: 18px 20px;
    margin: 8px 0;
    box-shadow: 0 4px 24px rgba(0,0,0,0.25), 0 0 1px rgba(200,255,87,0.05) inset;
}
.file-card-header {
    display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
}
.file-card-icon {
    width: 34px; height: 34px; border-radius: 8px;
    background: rgba(200,255,87,0.08);
    border: 1px solid rgba(200,255,87,0.2);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.7rem; color: var(--accent); flex-shrink: 0;
    font-family: 'DM Mono', monospace; font-weight: 500; letter-spacing: 0.05em;
    box-shadow: 0 0 10px rgba(200,255,87,0.08);
}
.file-card-meta { flex: 1; min-width: 0; }
.file-card-name {
    font-size: 0.84rem; font-weight: 600; color: var(--txt);
    letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.file-card-size {
    font-family: 'DM Mono', monospace;
    font-size: 0.56rem; color: var(--txt3); letter-spacing: 0.06em; margin-top: 2px;
}
.file-card-preview {
    background: rgba(7,7,10,0.6);
    border: 1px solid var(--line);
    border-radius: 7px;
    padding: 11px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 0.71rem; color: var(--txt2);
    line-height: 1.65; white-space: pre-wrap; word-break: break-word;
    max-height: 120px; overflow: hidden;
    margin-bottom: 14px;
    position: relative;
}
.file-card-preview::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 36px;
    background: linear-gradient(transparent, rgba(7,7,10,0.9));
    border-radius: 0 0 7px 7px;
}

/* download button inside card */
.file-card .stDownloadButton > button {
    all: unset !important;
    display: inline-flex !important; align-items: center !important; gap: 7px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.62rem !important; letter-spacing: 0.09em !important;
    color: #07070a !important;
    background: var(--accent) !important;
    border-radius: 7px !important;
    padding: 8px 16px !important; cursor: pointer !important;
    font-weight: 600 !important;
    box-shadow: 0 0 16px rgba(200,255,87,0.28), 0 2px 8px rgba(0,0,0,0.2) !important;
    transition: opacity 0.15s, box-shadow 0.15s !important;
}
.file-card .stDownloadButton > button:hover {
    opacity: 0.9 !important;
    box-shadow: 0 0 24px rgba(200,255,87,0.4), 0 2px 8px rgba(0,0,0,0.2) !important;
}

/* ════════════════════════════════
   FILE GENERATING CARD
════════════════════════════════ */
.file-gen-card {
    background: rgba(13,13,16,0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(200,255,87,0.15);
    border-radius: 12px;
    padding: 16px 18px;
    display: flex; align-items: center; gap: 14px;
    margin: 8px 0;
    box-shadow: 0 0 24px rgba(200,255,87,0.05), 0 4px 16px rgba(0,0,0,0.2);
}
.file-gen-icon {
    width: 36px; height: 36px; border-radius: 8px; flex-shrink: 0;
    background: rgba(200,255,87,0.07);
    border: 1px solid rgba(200,255,87,0.22);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 12px rgba(200,255,87,0.08);
}
.file-gen-icon svg { width: 15px; height: 15px; }
.file-gen-text { flex: 1; }
.file-gen-title {
    font-size: 0.82rem; font-weight: 600; color: var(--txt);
    letter-spacing: -0.01em; margin-bottom: 4px;
}
.file-gen-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.57rem; color: var(--accent); letter-spacing: 0.07em;
}
.file-gen-dots { display: flex; gap: 3px; align-items: center; }
.file-gen-dots span {
    display: block; width: 3px; height: 3px; border-radius: 50%;
    background: var(--accent);
    animation: tblink 1.1s ease-in-out infinite both;
    box-shadow: 0 0 4px var(--accent);
}
.file-gen-dots span:nth-child(2) { animation-delay: 0.18s; }
.file-gen-dots span:nth-child(3) { animation-delay: 0.36s; }

/* ════════════════════════════════
   FILE UPLOADER
════════════════════════════════ */
div[data-testid="stFileUploader"] > div {
    background: rgba(13,13,16,0.6) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px dashed rgba(255,255,255,0.1) !important;
    border-radius: var(--r) !important;
    padding: 12px 16px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
div[data-testid="stFileUploader"] > div:hover {
    border-color: rgba(200,255,87,0.25) !important;
    box-shadow: 0 0 16px rgba(200,255,87,0.05) !important;
}
div[data-testid="stFileUploader"] label,
div[data-testid="stFileUploader"] small {
    color: var(--txt2) !important;
    font-family: 'DM Sans', sans-serif !important; font-size: 0.78rem !important;
}

/* ════════════════════════════════
   CHAT INPUT — GLASS + GLOW
════════════════════════════════ */
div[data-testid="stChatInput"] {
    background: rgba(13,13,16,0.75) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35), 0 1px 0 rgba(255,255,255,0.03) inset !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
div[data-testid="stChatInput"]:focus-within {
    border-color: rgba(200,255,87,0.35) !important;
    box-shadow: 0 0 0 3px rgba(200,255,87,0.06), 0 0 24px rgba(200,255,87,0.08), 0 4px 24px rgba(0,0,0,0.35) !important;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important; color: var(--txt) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.895rem !important; caret-color: var(--accent) !important;
}
div[data-testid="stChatInput"] textarea::placeholder { color: var(--txt3) !important; }
div[data-testid="stChatInput"] button {
    background: var(--accent) !important; border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 0 14px rgba(200,255,87,0.3) !important;
    transition: box-shadow 0.15s !important;
}
div[data-testid="stChatInput"] button:hover {
    box-shadow: 0 0 22px rgba(200,255,87,0.45) !important;
}
div[data-testid="stChatInput"] button svg path { fill: #07070a !important; }

/* ════════════════════════════════
   ALERTS
════════════════════════════════ */
div[data-testid="stAlert"] {
    background: rgba(200,255,87,0.04) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(200,255,87,0.14) !important;
    border-radius: var(--r) !important;
    color: rgba(200,255,87,0.78) !important;
    font-family: 'DM Mono', monospace !important; font-size: 0.72rem !important;
    box-shadow: 0 0 16px rgba(200,255,87,0.04) !important;
}

/* ════════════════════════════════
   THINKING INDICATOR
════════════════════════════════ */
.thinking-row {
    display: inline-flex; align-items: center; gap: 10px; padding: 8px 0;
}
.t-dots { display: flex; gap: 4px; align-items: center; }
.t-dots span {
    display: block; width: 5px; height: 5px; border-radius: 50%;
    background: var(--accent);
    animation: tblink 1.1s ease-in-out infinite both;
    box-shadow: 0 0 6px var(--accent);
}
.t-dots span:nth-child(2) { animation-delay: 0.18s; }
.t-dots span:nth-child(3) { animation-delay: 0.36s; }
@keyframes tblink {
    0%, 80%, 100% { opacity: 0.12; transform: scale(0.7); box-shadow: none; }
    40% { opacity: 1; transform: scale(1); box-shadow: 0 0 8px var(--accent); }
}
.t-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem; color: var(--txt3);
    text-transform: uppercase; letter-spacing: 0.16em;
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
                <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6 1.5L10.5 6L6 10.5L1.5 6L6 1.5Z" fill="#07070a"/>
                    <circle cx="6" cy="6" r="1.8" fill="#07070a" opacity="0.5"/>
                </svg>
            </div>
            <span class="sb-name">Spartan AI</span>
        </div>
        <div class="sb-sub">Educational Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⌂  Home", key="sb_home"):
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
        Senior Project &nbsp;·&nbsp; 2025<br>
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
        <h1 class="home-h1">The classroom,<br><b>intelligently</b> <span class="glow-word">assisted.</span></h1>
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

    # hidden nav buttons (CSS hides them; kept so rerun can fire)
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

st.markdown(f"""
<div class="topbar">
    <div class="topbar-left">
        <div class="topbar-pill" style="color:{tmeta['color']}; border-color:{tmeta['color']}40;">{tmeta['tag']}</div>
        <div>
            <div class="topbar-title">{tool}</div>
            <div class="topbar-desc">{tmeta['desc']}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_assistant_message(msg["content"], i)
        else:
            st.markdown(msg.get("display_text", msg["content"]))

# ── Bottom input bar ──────────────────────────────────────────────────────────
bot_nc, bot_file, bot_chat = st.columns([1, 1, 14])

with bot_nc:
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button {
        all: unset !important;
        width: 40px !important; height: 40px !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        background: rgba(20,20,26,0.8) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255,255,255,0.09) !important;
        border-radius: 10px !important;
        cursor: pointer !important;
        color: var(--txt3) !important;
        font-size: 1.05rem !important;
        transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s !important;
        margin-top: 2px !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button:hover {
        background: rgba(200,255,87,0.08) !important;
        border-color: rgba(200,255,87,0.22) !important;
        color: var(--accent) !important;
        box-shadow: 0 0 14px rgba(200,255,87,0.12) !important;
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
        background: rgba(20,20,26,0.8) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255,255,255,0.09) !important;
        border-radius: 10px !important;
        padding: 0 !important;
        width: 40px !important; height: 40px !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        overflow: hidden !important;
        cursor: pointer !important;
        transition: background 0.15s, border-color 0.15s, box-shadow 0.15s !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div:hover {
        background: rgba(200,255,87,0.08) !important;
        border-color: rgba(200,255,87,0.22) !important;
        box-shadow: 0 0 14px rgba(200,255,87,0.12) !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] label,
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] small,
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] span:not([data-testid="stFileUploaderDropzone"]) {
        display: none !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] button {
        all: unset !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
        width: 40px !important; height: 40px !important;
        cursor: pointer !important;
        font-size: 1.05rem !important;
        color: var(--txt3) !important;
        transition: color 0.15s !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div:hover button {
        color: var(--accent) !important;
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] div[data-testid="stFileUploaderFile"] {
        position: absolute !important;
        width: 7px !important; height: 7px !important;
        background: var(--accent) !important;
        border-radius: 50% !important;
        top: 5px !important; right: 5px !important;
        overflow: hidden !important; font-size: 0 !important;
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

            stream_state  = "waiting"
            gen_slot      = None
            active_slot   = resp_slot

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
                "<span style='font-family:DM Mono,monospace;font-size:0.72rem;"
                "color:rgba(255,90,70,0.75);'>"
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
