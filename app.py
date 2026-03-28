# app.py — Spartan AI
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import re
import io
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
        "color": "#00c8ff",
        "index": "01",
        "icon":  "✦",
    },
    "Assignment Grader": {
        "tag":   "GRD",
        "desc":  "Upload student work and receive detailed rubric-aligned grading feedback.",
        "color": "#38e8c0",
        "index": "02",
        "icon":  "◈",
    },
    "AI Content Detector": {
        "tag":   "DET",
        "desc":  "Analyze submissions for AI-generated content and plagiarism signals.",
        "color": "#a78bfa",
        "index": "03",
        "icon":  "◉",
    },
    "Student Chatbot": {
        "tag":   "STU",
        "desc":  "A responsible, curriculum-aware assistant to support student learning.",
        "color": "#f472b6",
        "index": "04",
        "icon":  "◎",
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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap');

/* ══════════════════════════════════════════════════════
   TOKENS
══════════════════════════════════════════════════════ */
:root {
    --bg:          #020917;
    --bg1:         #040e22;
    --bg2:         #071428;
    --bg3:         #0a1c38;
    --bg4:         #0d2247;
    --blue:        #00b4ff;
    --blue-dim:    rgba(0,180,255,0.55);
    --blue-bg:     rgba(0,180,255,0.06);
    --blue-bd:     rgba(0,180,255,0.18);
    --blue-glow:   rgba(0,180,255,0.28);
    --cyan:        #06e5d4;
    --cyan-bg:     rgba(6,229,212,0.06);
    --txt:         rgba(200,225,255,0.93);
    --txt2:        rgba(100,145,200,0.65);
    --txt3:        rgba(50,90,150,0.50);
    --border:      rgba(0,120,200,0.14);
    --border-hi:   rgba(0,180,255,0.22);
    --scan:        rgba(0,180,255,0.018);
    --r:           8px;
}

/* ══════════════════════════════════════════════════════
   BASE
══════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
    background: var(--bg) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--txt) !important;
    -webkit-font-smoothing: antialiased !important;
}

/* Grid + scan lines + glow */
.stApp {
    background:
        radial-gradient(ellipse 60% 50% at 50% -5%, rgba(0,100,255,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 30% 40% at 90% 90%, rgba(0,220,200,0.04) 0%, transparent 50%),
        repeating-linear-gradient(0deg, var(--scan) 0px, var(--scan) 1px, transparent 1px, transparent 40px),
        repeating-linear-gradient(90deg, var(--scan) 0px, var(--scan) 1px, transparent 1px, transparent 40px),
        var(--bg) !important;
    background-attachment: fixed !important;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg1); }
::-webkit-scrollbar-thumb { background: var(--blue-bd); border-radius: 4px; }

#MainMenu, footer, header,
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; }

/* ══════════════════════════════════════════════════════
   SIDEBAR — CONTROL PANEL
══════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: rgba(4,14,34,0.92) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 4px 0 32px rgba(0,0,0,0.6), 1px 0 0 var(--border-hi) !important;
    width: 220px !important;
    min-width: 220px !important;
    max-width: 220px !important;
}
section[data-testid="stSidebar"] > div {
    padding: 0 !important;
    width: 220px !important;
    min-width: 220px !important;
    max-width: 220px !important;
    overflow-x: hidden !important;
}

/* Panel header */
.panel-header {
    padding: 22px 16px 18px;
    border-bottom: 1px solid var(--border);
    position: relative;
}
.panel-header::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, var(--blue), transparent);
    opacity: 0.35;
}
.ph-logo {
    display: flex; align-items: center; gap: 10px; margin-bottom: 6px;
}
.ph-hex {
    width: 32px; height: 32px;
    background: transparent;
    border: 1.5px solid var(--blue);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 12px var(--blue-glow), inset 0 0 8px rgba(0,180,255,0.06);
    position: relative;
}
.ph-hex::before {
    content: '';
    position: absolute; inset: 3px;
    border: 1px solid rgba(0,180,255,0.25);
    border-radius: 3px;
}
.ph-hex span {
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem; font-weight: 700;
    color: var(--blue); letter-spacing: 0.02em;
    position: relative; z-index: 1;
}
.ph-wordmark {
    line-height: 1;
}
.ph-name {
    font-size: 0.9rem; font-weight: 700; letter-spacing: -0.01em;
    color: var(--txt);
}
.ph-version {
    font-family: 'Space Mono', monospace;
    font-size: 0.45rem; color: var(--blue-dim);
    letter-spacing: 0.18em; text-transform: uppercase;
    margin-top: 2px;
}
.ph-status {
    display: flex; align-items: center; gap: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 0.48rem; color: var(--txt3);
    letter-spacing: 0.14em; text-transform: uppercase;
    padding-left: 42px;
}
.ph-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--cyan);
    box-shadow: 0 0 6px var(--cyan);
    animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* Section divider */
.panel-section {
    font-family: 'Space Mono', monospace;
    font-size: 0.46rem; letter-spacing: 0.25em; text-transform: uppercase;
    color: var(--txt3); padding: 16px 16px 5px;
    display: flex; align-items: center; gap: 8px;
}
.panel-section::after {
    content: '';
    flex: 1; height: 1px;
    background: var(--border);
}

/* Nav buttons */
div[data-testid="stSidebar"] .stButton {
    width: 100% !important;
    padding: 0 10px !important;
    margin: 0 !important;
}
div[data-testid="stSidebar"] .stButton > button {
    all: unset !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    padding: 8px 10px !important;
    margin: 1px 0 !important;
    border-radius: 6px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 400 !important;
    color: var(--txt2) !important;
    cursor: pointer !important;
    line-height: 1 !important;
    transition: all 0.15s !important;
    border-left: 2px solid transparent !important;
    box-sizing: border-box !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--blue-bg) !important;
    border-left-color: var(--blue) !important;
    color: var(--txt) !important;
    box-shadow: inset 0 0 20px rgba(0,180,255,0.04) !important;
    padding-left: 14px !important;
}

/* Panel footer */
.panel-foot {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 10px 16px 14px;
    border-top: 1px solid var(--border);
    background: rgba(2,9,23,0.6);
}
.panel-foot-line {
    font-family: 'Space Mono', monospace;
    font-size: 0.46rem; color: var(--txt3);
    letter-spacing: 0.1em; line-height: 2;
    text-transform: uppercase;
}
div[data-testid="stSidebar"] > div > div {
    padding-bottom: 62px !important;
}

/* ══════════════════════════════════════════════════════
   MAIN CONTENT
══════════════════════════════════════════════════════ */
.main .block-container {
    max-width: 860px !important;
    padding: 0 2.5rem 9rem !important;
}

/* ══════════════════════════════════════════════════════
   HOME — MISSION CONTROL
══════════════════════════════════════════════════════ */
.mc-header {
    padding: 52px 0 44px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 40px;
    position: relative;
}
.mc-header::after {
    content: '';
    position: absolute; bottom: -1px; left: 0;
    width: 120px; height: 1px;
    background: linear-gradient(90deg, var(--blue), transparent);
}
.mc-sys {
    font-family: 'Space Mono', monospace;
    font-size: 0.5rem; letter-spacing: 0.3em; text-transform: uppercase;
    color: var(--blue-dim); margin-bottom: 16px;
    display: flex; align-items: center; gap: 10px;
}
.mc-sys::before {
    content: '//';
    color: var(--blue);
    font-weight: 700;
}
.mc-title {
    font-size: 3.2rem; font-weight: 700; line-height: 1;
    letter-spacing: -0.04em;
    color: var(--txt); margin-bottom: 6px;
}
.mc-title .blue { color: var(--blue); }
.mc-title .dim  { font-weight: 300; color: var(--txt2); }
.mc-sub {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem; color: var(--txt3);
    letter-spacing: 0.08em; margin-top: 18px;
    max-width: 480px; line-height: 1.8;
}

/* Module grid — all in one HTML block */
.module-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 44px;
    box-shadow: 0 0 0 1px rgba(0,180,255,0.05);
}
.module {
    background: var(--bg1);
    padding: 28px 26px;
    position: relative;
    transition: background 0.2s;
    overflow: hidden;
}
.module::before {
    content: '';
    position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
    background: currentColor;
    opacity: 0;
    transition: opacity 0.2s;
}
.module:hover { background: var(--bg2); }
.module:hover::before { opacity: 0.7; }
.mod-idx {
    font-family: 'Space Mono', monospace;
    font-size: 0.5rem; letter-spacing: 0.2em;
    color: var(--txt3); margin-bottom: 16px;
    text-transform: uppercase;
}
.mod-tag {
    display: inline-flex; align-items: center; gap: 5px;
    font-family: 'Space Mono', monospace;
    font-size: 0.55rem; font-weight: 700; letter-spacing: 0.12em;
    padding: 3px 9px;
    background: rgba(0,0,0,0.3);
    border: 1px solid currentColor;
    border-radius: 3px;
    margin-bottom: 14px;
}
.mod-tag::before {
    content: '';
    width: 4px; height: 4px; border-radius: 50%;
    background: currentColor;
}
.mod-name {
    font-size: 1rem; font-weight: 600; letter-spacing: -0.02em;
    color: var(--txt); margin-bottom: 8px;
}
.mod-desc {
    font-size: 0.75rem; color: var(--txt2);
    line-height: 1.65; font-weight: 300;
}
.mod-corner {
    position: absolute; bottom: 18px; right: 18px;
    font-family: 'Space Mono', monospace;
    font-size: 1.4rem; opacity: 0.06; color: currentColor;
    line-height: 1;
}

/* Home footer */
.mc-footer {
    display: flex; align-items: center; justify-content: space-between;
    padding-top: 20px;
    border-top: 1px solid var(--border);
}
.mc-foot-txt {
    font-family: 'Space Mono', monospace;
    font-size: 0.48rem; color: var(--txt3);
    letter-spacing: 0.12em; text-transform: uppercase;
}
.mc-foot-badge {
    font-family: 'Space Mono', monospace;
    font-size: 0.46rem; letter-spacing: 0.15em;
    color: var(--blue-dim);
    border: 1px solid var(--border-hi);
    padding: 2px 8px; border-radius: 3px;
    text-transform: uppercase;
}

/* Hide invisible home nav buttons */
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton,
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton > button {
    display: none !important; height: 0 !important;
    padding: 0 !important; margin: 0 !important;
    overflow: hidden !important;
}

/* ══════════════════════════════════════════════════════
   TOOL HEADER — BREADCRUMB
══════════════════════════════════════════════════════ */
.tool-header {
    padding: 24px 0 20px;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border);
    position: relative;
}
.tool-header::after {
    content: '';
    position: absolute; bottom: -1px; left: 0;
    width: 50px; height: 1px;
    background: var(--blue);
    box-shadow: 0 0 8px var(--blue);
}
.th-crumb {
    font-family: 'Space Mono', monospace;
    font-size: 0.5rem; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--txt3); margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}
.th-crumb .sep { color: var(--blue); opacity: 0.5; }
.th-crumb .active { color: var(--blue-dim); }
.th-main { display: flex; align-items: center; gap: 14px; }
.th-tag {
    font-family: 'Space Mono', monospace;
    font-size: 0.55rem; font-weight: 700; letter-spacing: 0.1em;
    padding: 4px 10px; border-radius: 4px;
    border: 1px solid currentColor;
    flex-shrink: 0;
}
.th-name {
    font-size: 1.15rem; font-weight: 700;
    letter-spacing: -0.025em; color: var(--txt);
}
.th-desc {
    font-family: 'Space Mono', monospace;
    font-size: 0.58rem; color: var(--txt3);
    margin-top: 3px; letter-spacing: 0.04em; line-height: 1.6;
}
.th-status {
    margin-left: auto;
    display: flex; align-items: center; gap: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 0.46rem; color: var(--cyan);
    letter-spacing: 0.15em; text-transform: uppercase;
    flex-shrink: 0;
}
.th-status-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: var(--cyan);
    box-shadow: 0 0 6px var(--cyan);
    animation: pulse 2.4s ease-in-out infinite;
}

/* ══════════════════════════════════════════════════════
   CHAT MESSAGES
══════════════════════════════════════════════════════ */
.stChatMessage {
    background: transparent !important;
    border: none !important;
    padding: 5px 0 !important;
    gap: 10px !important;
}

/* Override avatar */
div[data-testid="chatAvatarIcon-user"],
div[data-testid="chatAvatarIcon-assistant"] {
    width: 28px !important; height: 28px !important;
    border-radius: 6px !important;
    overflow: hidden !important; flex-shrink: 0 !important;
}
div[data-testid="chatAvatarIcon-user"] img,
div[data-testid="chatAvatarIcon-assistant"] img,
div[data-testid="chatAvatarIcon-user"] svg,
div[data-testid="chatAvatarIcon-assistant"] svg {
    filter: saturate(0) brightness(0.4) !important;
    width: 100% !important; height: 100% !important;
}
div[data-testid="chatAvatarIcon-user"] {
    background: rgba(0,180,255,0.08) !important;
    border: 1px solid var(--blue-bd) !important;
    box-shadow: 0 0 8px rgba(0,180,255,0.08) !important;
}
div[data-testid="chatAvatarIcon-assistant"] {
    background: rgba(6,229,212,0.06) !important;
    border: 1px solid rgba(6,229,212,0.2) !important;
}

/* User message */
div[data-testid="stChatMessageUser"] {
    flex-direction: row-reverse !important;
}
div[data-testid="stChatMessageUser"] > div[data-testid="stChatMessageContent"] {
    background: rgba(0,180,255,0.06) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--blue-bd) !important;
    border-radius: 12px 2px 12px 12px !important;
    padding: 12px 16px !important;
    max-width: 72% !important;
    font-size: 0.875rem !important;
    line-height: 1.68 !important;
    color: var(--txt) !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.3) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* Assistant message */
div[data-testid="stChatMessageAssistant"] > div[data-testid="stChatMessageContent"] {
    background: rgba(4,14,34,0.7) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border-hi) !important;
    border-left: 2px solid var(--cyan) !important;
    border-radius: 2px 12px 12px 12px !important;
    padding: 14px 18px !important;
    max-width: 88% !important;
    font-size: 0.875rem !important;
    line-height: 1.75 !important;
    color: rgba(210,230,255,0.93) !important;
    box-shadow: 0 2px 16px rgba(0,0,0,0.25), 0 0 0 1px rgba(6,229,212,0.04) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ══════════════════════════════════════════════════════
   FILE DOWNLOAD CARD
══════════════════════════════════════════════════════ */
.fcard {
    background: var(--bg2);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-hi);
    border-left: 2px solid var(--blue);
    border-radius: 8px;
    padding: 18px 20px;
    margin: 8px 0;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3), 0 0 20px rgba(0,180,255,0.04);
}
.fcard-hd { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.fcard-icon {
    width: 36px; height: 36px; border-radius: 6px; flex-shrink: 0;
    background: var(--blue-bg); border: 1px solid var(--blue-bd);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Space Mono', monospace;
    font-size: 0.6rem; font-weight: 700;
    color: var(--blue);
    box-shadow: 0 0 10px rgba(0,180,255,0.08);
}
.fcard-name {
    font-size: 0.85rem; font-weight: 600; color: var(--txt); letter-spacing: -0.01em;
}
.fcard-meta {
    font-family: 'Space Mono', monospace;
    font-size: 0.52rem; color: var(--txt3); letter-spacing: 0.06em; margin-top: 3px;
}
.fcard-preview {
    background: rgba(2,9,23,0.7);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 10px 14px;
    font-family: 'Space Mono', monospace;
    font-size: 0.67rem; color: var(--txt2);
    line-height: 1.65; white-space: pre-wrap; word-break: break-word;
    max-height: 110px; overflow: hidden;
    margin-bottom: 14px; position: relative;
}
.fcard-preview::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 30px;
    background: linear-gradient(transparent, rgba(2,9,23,0.9));
    border-radius: 0 0 5px 5px;
}
.fcard .stDownloadButton > button {
    all: unset !important;
    display: inline-flex !important; align-items: center !important; gap: 7px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.58rem !important; letter-spacing: 0.1em !important;
    color: var(--bg) !important;
    background: var(--blue) !important;
    border-radius: 5px !important;
    padding: 8px 16px !important; cursor: pointer !important;
    font-weight: 700 !important;
    box-shadow: 0 0 16px rgba(0,180,255,0.3) !important;
    transition: box-shadow 0.15s, opacity 0.15s !important;
}
.fcard .stDownloadButton > button:hover {
    box-shadow: 0 0 28px rgba(0,180,255,0.5) !important;
    opacity: 0.92 !important;
}

/* ══════════════════════════════════════════════════════
   FILE GENERATING CARD
══════════════════════════════════════════════════════ */
.fgen {
    background: var(--bg2);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-hi);
    border-left: 2px solid var(--cyan);
    border-radius: 8px;
    padding: 16px 18px;
    display: flex; align-items: center; gap: 14px;
    margin: 8px 0;
    box-shadow: 0 0 20px rgba(6,229,212,0.05);
}
.fgen-icon {
    width: 38px; height: 38px; border-radius: 6px; flex-shrink: 0;
    background: var(--cyan-bg); border: 1px solid rgba(6,229,212,0.22);
    display: flex; align-items: center; justify-content: center;
}
.fgen-icon svg { width: 16px; height: 16px; }
.fgen-title { font-size: 0.82rem; font-weight: 600; color: var(--txt); margin-bottom: 4px; }
.fgen-sub {
    font-family: 'Space Mono', monospace;
    font-size: 0.54rem; color: var(--cyan); letter-spacing: 0.08em;
    display: flex; align-items: center; gap: 7px;
}
.fdots { display: flex; gap: 3px; }
.fdots span {
    display: block; width: 3px; height: 3px; border-radius: 50%;
    background: var(--cyan);
    animation: blink 1.1s ease-in-out infinite both;
}
.fdots span:nth-child(2) { animation-delay: 0.2s; }
.fdots span:nth-child(3) { animation-delay: 0.4s; }

/* ══════════════════════════════════════════════════════
   THINKING INDICATOR
══════════════════════════════════════════════════════ */
.thinking {
    display: inline-flex; align-items: center; gap: 10px; padding: 8px 0;
}
.tdots { display: flex; gap: 5px; align-items: center; }
.tdots span {
    display: block; width: 6px; height: 6px; border-radius: 50%;
    background: var(--blue);
    animation: blink 1.1s ease-in-out infinite both;
    box-shadow: 0 0 6px var(--blue);
}
.tdots span:nth-child(2) { animation-delay: 0.2s; }
.tdots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
    0%, 80%, 100% { opacity: 0.12; transform: scale(0.65); }
    40% { opacity: 1; transform: scale(1); }
}
.thinking-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.56rem; color: var(--txt3);
    text-transform: uppercase; letter-spacing: 0.2em;
}

/* ══════════════════════════════════════════════════════
   FILE UPLOADER (icon button)
══════════════════════════════════════════════════════ */
div[data-testid="stFileUploader"] > div {
    background: rgba(4,14,34,0.8) !important;
    border: 1px dashed var(--border-hi) !important;
    border-radius: var(--r) !important;
    padding: 10px 14px !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stFileUploader"] > div:hover {
    border-color: var(--blue-bd) !important;
    box-shadow: 0 0 12px rgba(0,180,255,0.06) !important;
}
div[data-testid="stFileUploader"] label,
div[data-testid="stFileUploader"] small {
    color: var(--txt2) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.77rem !important;
}

/* ══════════════════════════════════════════════════════
   CHAT INPUT — command bar
══════════════════════════════════════════════════════ */
div[data-testid="stChatInput"] {
    background: rgba(4,14,34,0.9) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(0,180,255,0.04) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
div[data-testid="stChatInput"]:focus-within {
    border-color: rgba(0,180,255,0.35) !important;
    box-shadow: 0 4px 32px rgba(0,0,0,0.4), 0 0 0 3px rgba(0,180,255,0.07), 0 0 18px rgba(0,180,255,0.08) !important;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--txt) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.9rem !important;
    caret-color: var(--blue) !important;
}
div[data-testid="stChatInput"] textarea::placeholder {
    color: var(--txt3) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.03em !important;
}
div[data-testid="stChatInput"] button {
    background: var(--blue) !important;
    border: none !important;
    border-radius: 6px !important;
    width: 30px !important; height: 30px !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    box-shadow: 0 0 14px rgba(0,180,255,0.3) !important;
    transition: box-shadow 0.15s !important;
    flex-shrink: 0 !important;
    margin: auto 6px auto 0 !important;
}
div[data-testid="stChatInput"] button:hover {
    box-shadow: 0 0 24px rgba(0,180,255,0.5) !important;
}
div[data-testid="stChatInput"] button svg {
    width: 13px !important; height: 13px !important;
}
div[data-testid="stChatInput"] button svg path,
div[data-testid="stChatInput"] button svg rect {
    fill: #020917 !important;
    stroke: none !important;
}

/* ══════════════════════════════════════════════════════
   BOTTOM BAR — icon action buttons
══════════════════════════════════════════════════════ */
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

/* ══════════════════════════════════════════════════════
   ALERTS
══════════════════════════════════════════════════════ */
div[data-testid="stAlert"] {
    background: var(--blue-bg) !important;
    border: 1px solid var(--blue-bd) !important;
    border-radius: var(--r) !important;
    color: var(--blue-dim) !important;
    font-family: 'Space Mono', monospace !important;
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
    st.session_state.messages           = [{"role": "assistant", "content": "[output-text]System online. How can I assist you today?[/output-text]"}]
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
      <div class="fcard-meta">{size_kb} KB &middot; OUTPUT READY</div>
    </div>
  </div>
  <div class="fcard-preview">{preview}</div>
</div>
""", unsafe_allow_html=True)
            file_bytes, mime = make_download_bytes(content, ext)
            st.download_button(
                label=f"↓  DOWNLOAD  {fname}",
                data=file_bytes,
                file_name=fname,
                mime=mime,
                key=f"dl_{msg_index}_{seg_i}_{ext}",
            )

# ── SIDEBAR — Control Panel ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="panel-header">
  <div class="ph-logo">
    <div class="ph-hex"><span>S</span></div>
    <div class="ph-wordmark">
      <div class="ph-name">Spartan AI</div>
      <div class="ph-version">System v1.0</div>
    </div>
  </div>
  <div class="ph-status"><div class="ph-dot"></div>All systems operational</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="panel-section">Navigate</div>', unsafe_allow_html=True)

    if st.button("⌂  Home", key="sb_home"):
        st.session_state.mode               = "Home"
        st.session_state.messages           = []
        st.session_state.pending_ocr_text   = None
        st.session_state.uploaded_file_name = None
        st.rerun()

    st.markdown('<div class="panel-section">Modules</div>', unsafe_allow_html=True)

    for tool_name, tmeta in TOOL_META.items():
        label = f"{tmeta['icon']}  {tmeta['index']} · {tool_name}"
        if st.button(label, key=f"sb_{tool_name}"):
            go_to_tool(tool_name)
            st.rerun()

    st.markdown("""
<div class="panel-foot">
  <div class="panel-foot-line">Senior Project · 2025</div>
  <div class="panel-foot-line">Dallin Geurts</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HOME — MISSION CONTROL
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Home":

    # Build all module cards in one HTML string so grid works
    modules_html = ""
    for name, tmeta in TOOL_META.items():
        modules_html += f"""
<div class="module" style="color:{tmeta['color']};">
  <div class="mod-idx">MODULE {tmeta['index']}</div>
  <div class="mod-tag">{tmeta['tag']}</div>
  <div class="mod-name">{name}</div>
  <div class="mod-desc">{tmeta['desc']}</div>
  <div class="mod-corner">{tmeta['icon']}</div>
</div>"""

    st.markdown(f"""
<div class="mc-header">
  <div class="mc-sys">Educational Intelligence Platform</div>
  <div class="mc-title"><span class="dim">SPARTAN</span> <span class="blue">AI</span></div>
  <div class="mc-sub">
    Four specialized AI modules for educators and students.<br>
    Select a module from the control panel or below to begin.
  </div>
</div>
<div class="module-grid">{modules_html}</div>
<div class="mc-footer">
  <div class="mc-foot-txt">Spartan AI · Dallin Geurts · 2025</div>
  <div class="mc-foot-badge">v1.0 · READY</div>
</div>
""", unsafe_allow_html=True)

    # Hidden nav buttons
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
<div class="tool-header">
  <div class="th-crumb">
    Spartan AI <span class="sep">/</span> <span class="active">{tmeta['tag']}</span>
  </div>
  <div class="th-main">
    <div class="th-tag" style="color:{tmeta['color']}; border-color:{tmeta['color']}40;">{tmeta['tag']}</div>
    <div>
      <div class="th-name">{tool}</div>
      <div class="th-desc">{tmeta['desc']}</div>
    </div>
    <div class="th-status">
      <div class="th-status-dot"></div>Online
    </div>
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

# ── Bottom bar ────────────────────────────────────────────────────────────────
bot_nc, bot_file, bot_chat = st.columns([1, 1, 14])

with bot_nc:
    st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button {
    all: unset !important;
    width: 40px !important; height: 40px !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    background: rgba(4,14,34,0.9) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    font-size: 1.05rem !important;
    color: var(--txt3) !important;
    transition: all 0.15s !important;
    box-sizing: border-box !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton > button:hover {
    background: var(--blue-bg) !important;
    border-color: var(--blue-bd) !important;
    color: var(--blue) !important;
    box-shadow: 0 0 14px rgba(0,180,255,0.12) !important;
}
</style>
""", unsafe_allow_html=True)
    if st.button("↺", key="new_chat", help="New session"):
        go_to_tool(tool)
        st.rerun()

with bot_file:
    st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] {
    width: 40px !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div {
    background: rgba(4,14,34,0.9) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border-hi) !important;
    border-radius: 8px !important;
    padding: 0 !important;
    width: 40px !important; height: 40px !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    overflow: hidden !important; cursor: pointer !important;
    transition: all 0.15s !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div:hover {
    background: var(--blue-bg) !important;
    border-color: var(--blue-bd) !important;
    box-shadow: 0 0 14px rgba(0,180,255,0.12) !important;
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
    cursor: pointer !important; font-size: 1rem !important; color: var(--txt3) !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] > div:hover button {
    color: var(--blue) !important;
}
div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
    position: absolute !important;
    width: 7px !important; height: 7px !important;
    background: var(--cyan) !important;
    border-radius: 50% !important;
    top: 4px !important; right: 4px !important;
    overflow: hidden !important; font-size: 0 !important;
    box-shadow: 0 0 6px var(--cyan) !important;
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
    user_input = st.chat_input("> _ input command…")

# ── Process uploaded file ─────────────────────────────────────────────────────
if uploaded_file is not None and uploaded_file.name != st.session_state.uploaded_file_name:
    with st.spinner("Processing file…"):
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
            st.toast(f"FILE LOADED: {uploaded_file.name}", icon="📎")
        except Exception as e:
            st.error(f"File read error: {e}")

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
  <div class="thinking-label">Processing query</div>
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
      <path d="M3 2h7l4 4v9H3V2z" stroke="#06e5d4" stroke-width="1.2" stroke-linejoin="round"/>
      <path d="M10 2v4h4" stroke="#06e5d4" stroke-width="1.2" stroke-linejoin="round"/>
      <path d="M5 9h6M5 11.5h4" stroke="#06e5d4" stroke-width="1" stroke-linecap="round"/>
    </svg>
  </div>
  <div>
    <div class="fgen-title">Generating output file…</div>
    <div class="fgen-sub">
      Writing document
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
                "<span style='font-family:Space Mono,monospace;font-size:0.68rem;"
                "color:rgba(255,70,70,0.75);letter-spacing:0.06em;'>"
                "ERR &nbsp;// &nbsp;Connection failed — check server status."
                "</span>",
                unsafe_allow_html=True,
            )

    if full_response:
        st.session_state.messages.append({
            "role":         "assistant",
            "content":      full_response,
            "display_text": full_response,
        })
