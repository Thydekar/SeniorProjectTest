# app.py — Spartan AI · Full Glass UI Redesign
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import warnings

# Suppress SSL warnings from verify=False
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

from PIL import Image

# ── Optional dependencies with graceful fallback ──────────────────────────────
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx as docx_module   # FIX: alias so it doesn't shadow the name
except ImportError:
    docx_module = None

try:
    import pytesseract
    TESSERACT_OK = True
except ImportError:
    pytesseract = None
    TESSERACT_OK = False

# ── Config ───────────────────────────────────────────────────────────────────
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
        "desc": "Generate custom assignments, rubrics, and prompts for any subject or grade.",
        "glow": "rgba(99,179,237,0.35)",
        "accent": "#63b3ed",
        "orb": "radial-gradient(circle, rgba(99,179,237,0.18) 0%, transparent 70%)",
    },
    "Assignment Grader": {
        "icon": "◈",
        "desc": "Upload student work and receive detailed rubric-aligned grading feedback.",
        "glow": "rgba(104,211,145,0.35)",
        "accent": "#68d391",
        "orb": "radial-gradient(circle, rgba(104,211,145,0.18) 0%, transparent 70%)",
    },
    "AI Content Detector": {
        "icon": "◉",
        "desc": "Analyze submissions for AI-generated content and plagiarism signals.",
        "glow": "rgba(252,129,74,0.35)",
        "accent": "#fc814a",
        "orb": "radial-gradient(circle, rgba(252,129,74,0.18) 0%, transparent 70%)",
    },
    "Student Chatbot": {
        "icon": "◎",
        "desc": "A responsible, curriculum-aware assistant to support student learning.",
        "glow": "rgba(183,148,244,0.35)",
        "accent": "#b794f4",
        "orb": "radial-gradient(circle, rgba(183,148,244,0.18) 0%, transparent 70%)",
    },
}
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME  = "dgeurts"
PASSWORD  = "thaidakar21"
OCR_CONFIG = r"--oem 3 --psm 6"

st.set_page_config(page_title="Spartan AI", layout="wide", initial_sidebar_state="expanded")

# ── MASTER CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=Figtree:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root {
    --glass-bg:     rgba(255,255,255,0.04);
    --glass-border: rgba(255,255,255,0.09);
    --glass-blur:   20px;
    --glass-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
    --bg-deep:      #05070f;
    --text-primary: rgba(235,242,255,0.92);
    --text-muted:   rgba(180,195,230,0.45);
    --text-subtle:  rgba(150,168,210,0.28);
    --radius-lg:    18px;
    --radius-md:    12px;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    background-color: var(--bg-deep) !important;
    font-family: 'Figtree', sans-serif !important;
    color: var(--text-primary) !important;
}

/* ── Aurora background ── */
.stApp::before {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
        radial-gradient(ellipse 80% 60% at 15% 20%, rgba(99,102,241,0.13) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 85% 75%, rgba(183,148,244,0.10) 0%, transparent 55%),
        radial-gradient(ellipse 50% 40% at 55% 45%, rgba(99,179,237,0.07) 0%, transparent 60%);
    animation: aurora 18s ease-in-out infinite alternate;
}
@keyframes aurora {
    0%   { transform: scale(1) rotate(0deg); opacity: 1; }
    33%  { transform: scale(1.04) rotate(0.5deg); opacity: 0.85; }
    66%  { transform: scale(0.97) rotate(-0.5deg); }
    100% { transform: scale(1.02) rotate(0.3deg); opacity: 0.9; }
}

/* Grain overlay */
.stApp::after {
    content: '';
    position: fixed; inset: 0; z-index: 1; pointer-events: none; opacity: 0.3;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: rgba(8,10,20,0.75) !important;
    backdrop-filter: blur(28px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(28px) saturate(160%) !important;
    border-right: 1px solid rgba(255,255,255,0.055) !important;
    box-shadow: 4px 0 48px rgba(0,0,0,0.55) !important;
    z-index: 100;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }

.sb-logo {
    padding: 30px 24px 22px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.sb-mark {
    width: 38px; height: 38px;
    border-radius: 11px;
    background: linear-gradient(135deg, #6366f1 0%, #b794f4 100%);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Outfit', sans-serif;
    font-weight: 900; font-size: 1.05rem; color: white;
    box-shadow: 0 4px 20px rgba(99,102,241,0.45);
    margin-bottom: 13px;
}
.sb-logo h2 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important; font-size: 1.1rem !important;
    color: var(--text-primary) !important; letter-spacing: -0.03em;
    margin: 0 0 3px !important;
}
.sb-logo p { font-size: 0.67rem; color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.12em; margin: 0; }

.sb-label {
    font-size: 0.61rem; font-weight: 600; color: var(--text-subtle);
    text-transform: uppercase; letter-spacing: 0.14em; padding: 18px 24px 7px;
}

div[data-testid="stSidebar"] .stButton > button {
    background: transparent !important; border: none !important;
    border-radius: 10px !important; color: var(--text-muted) !important;
    font-family: 'Figtree', sans-serif !important; font-size: 0.875rem !important;
    font-weight: 500 !important; padding: 11px 18px !important;
    width: calc(100% - 16px) !important; margin: 1px 8px !important;
    text-align: left !important; transition: all 0.18s ease !important;
}
div[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.055) !important;
    color: var(--text-primary) !important;
    box-shadow: none !important; border: none !important;
}
div[data-testid="stSidebar"] .stButton > button:focus { box-shadow: none !important; outline: none !important; }

.sb-foot {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 18px 24px; border-top: 1px solid rgba(255,255,255,0.04);
    font-size: 0.7rem; color: var(--text-subtle); line-height: 1.7;
}

/* ── Main ── */
.main .block-container {
    max-width: 830px !important;
    padding: 2.5rem 2rem 8rem !important;
    position: relative; z-index: 2;
}

/* ── Tool header ── */
.tool-header {
    background: rgba(255,255,255,0.035);
    backdrop-filter: blur(22px) saturate(160%);
    -webkit-backdrop-filter: blur(22px) saturate(160%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: var(--radius-lg);
    box-shadow: var(--glass-shadow);
    padding: 20px 24px; margin-bottom: 22px;
    display: flex; align-items: center; gap: 16px;
    position: relative; overflow: hidden;
}
.tool-header::before {
    content: ''; position: absolute; top: -60px; right: -60px;
    width: 240px; height: 240px; border-radius: 50%;
    background: var(--orb); pointer-events: none;
}
.th-icon {
    width: 50px; height: 50px; border-radius: 14px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 1.4rem;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
    backdrop-filter: blur(8px);
}
.th-title {
    font-family: 'Outfit', sans-serif !important; font-weight: 700 !important;
    font-size: 1.45rem !important; color: var(--text-primary) !important;
    letter-spacing: -0.03em; margin: 0 !important;
}
.th-desc { font-size: 0.79rem !important; color: var(--text-muted) !important; margin: 3px 0 0 !important; }

/* ── New Chat button ── */
.nc-wrap .stButton > button {
    background: rgba(255,255,255,0.055) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important; color: rgba(210,225,255,0.65) !important;
    font-family: 'Figtree', sans-serif !important; font-size: 0.78rem !important;
    font-weight: 500 !important; padding: 8px 16px !important; width: auto !important;
    transition: all 0.2s ease !important;
}
.nc-wrap .stButton > button:hover {
    background: rgba(255,255,255,0.09) !important;
    border-color: rgba(255,255,255,0.16) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
}

/* ── Chat messages ── */
.stChatMessage { background: transparent !important; border: none !important; padding: 6px 0 !important; gap: 12px !important; }

div[data-testid="stChatMessageUser"] { flex-direction: row-reverse !important; }
div[data-testid="stChatMessageUser"] > div[data-testid="stChatMessageContent"] {
    background: linear-gradient(135deg, rgba(99,102,241,0.22), rgba(139,92,246,0.17)) !important;
    backdrop-filter: blur(16px) !important; -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(139,92,246,0.22) !important;
    border-radius: 20px 20px 4px 20px !important;
    box-shadow: 0 4px 24px rgba(99,102,241,0.14), inset 0 1px 0 rgba(255,255,255,0.08) !important;
    padding: 12px 18px !important; max-width: 70% !important;
    color: rgba(235,242,255,0.95) !important; font-size: 0.9rem !important; line-height: 1.65 !important;
}

div[data-testid="stChatMessageAssistant"] > div[data-testid="stChatMessageContent"] {
    background: rgba(255,255,255,0.035) !important;
    backdrop-filter: blur(16px) !important; -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255,255,255,0.075) !important;
    border-radius: 20px 20px 20px 4px !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.05) !important;
    padding: 14px 20px !important; max-width: 78% !important;
    color: rgba(215,228,255,0.9) !important; font-size: 0.9rem !important; line-height: 1.72 !important;
}

div[data-testid="chatAvatarIcon-user"],
div[data-testid="chatAvatarIcon-assistant"] {
    background: rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3) !important;
}

/* ── File uploader ── */
div[data-testid="stFileUploader"] > div {
    background: rgba(255,255,255,0.025) !important;
    backdrop-filter: blur(14px) !important;
    border: 1.5px dashed rgba(255,255,255,0.09) !important;
    border-radius: var(--radius-md) !important;
    padding: 18px 22px !important; transition: all 0.25s ease !important;
}
div[data-testid="stFileUploader"] > div:hover {
    background: rgba(255,255,255,0.045) !important;
    border-color: rgba(99,102,241,0.38) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.07), 0 4px 20px rgba(0,0,0,0.3) !important;
}
div[data-testid="stFileUploader"] label, div[data-testid="stFileUploader"] small {
    color: var(--text-muted) !important; font-family: 'Figtree', sans-serif !important; font-size: 0.82rem !important;
}

/* ── Chat input ── */
div[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.045) !important;
    backdrop-filter: blur(22px) !important; -webkit-backdrop-filter: blur(22px) !important;
    border: 1px solid rgba(255,255,255,0.095) !important; border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.07) !important;
    transition: all 0.25s ease !important;
}
div[data-testid="stChatInput"]:focus-within {
    border-color: rgba(99,102,241,0.42) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.09), 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.07) !important;
}
div[data-testid="stChatInput"] textarea {
    background: transparent !important; color: var(--text-primary) !important;
    font-family: 'Figtree', sans-serif !important; font-size: 0.92rem !important; caret-color: #6366f1 !important;
}
div[data-testid="stChatInput"] textarea::placeholder { color: rgba(150,168,210,0.28) !important; }
div[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important; border-radius: 10px !important;
    box-shadow: 0 2px 14px rgba(99,102,241,0.38) !important;
}

/* ── Alerts ── */
div[data-testid="stAlert"] {
    background: rgba(104,211,145,0.07) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(104,211,145,0.16) !important;
    border-radius: var(--radius-md) !important;
    color: #68d391 !important;
    font-size: 0.83rem !important; font-family: 'Figtree', sans-serif !important;
}

/* ── Home page ── */
.home-kicker {
    display: inline-block;
    background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.2);
    backdrop-filter: blur(10px); border-radius: 100px;
    padding: 5px 16px; font-size: 0.7rem; font-weight: 600;
    color: rgba(165,155,255,0.75); text-transform: uppercase; letter-spacing: 0.13em;
    margin-bottom: 22px;
}
.home-h1 {
    font-family: 'Outfit', sans-serif !important; font-weight: 900 !important;
    font-size: 3.7rem !important; line-height: 1.04 !important;
    letter-spacing: -0.055em !important; color: var(--text-primary) !important;
    margin-bottom: 20px !important;
}
.home-h1 .grad {
    background: linear-gradient(135deg, #93c5fd 0%, #a78bfa 50%, #f472b6 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.home-sub {
    font-size: 1.05rem !important; color: var(--text-muted) !important;
    max-width: 500px; margin: 0 auto 48px !important; line-height: 1.74 !important; font-weight: 300 !important;
}

.cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 48px; }
.tool-card {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
    border: 1px solid rgba(255,255,255,0.07); border-radius: var(--radius-lg);
    padding: 26px 24px; position: relative; overflow: hidden;
    box-shadow: 0 4px 28px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05);
    transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}
.tool-card::before {
    content: ''; position: absolute; top: -70px; right: -70px;
    width: 240px; height: 240px; border-radius: 50%;
    background: var(--card-orb); pointer-events: none;
}
.tool-card:hover {
    transform: translateY(-3px);
    border-color: rgba(255,255,255,0.12);
    box-shadow: 0 14px 44px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.07);
}
.card-icon {
    width: 44px; height: 44px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center; font-size: 1.25rem;
    margin-bottom: 16px; background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(8px);
}
.card-name { font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 1rem; color: var(--text-primary); letter-spacing: -0.02em; margin-bottom: 8px; }
.card-desc { font-size: 0.8rem; color: var(--text-muted); line-height: 1.6; font-weight: 300; }
.card-arrow { position: absolute; bottom: 22px; right: 22px; font-size: 1rem; color: rgba(255,255,255,0.1); }

.home-hr { border: none; border-top: 1px solid rgba(255,255,255,0.05); margin: 0 0 22px; }
.home-footer { text-align: center; font-size: 0.72rem; color: var(--text-subtle); letter-spacing: 0.06em; padding-bottom: 8px; }

/* ── Thinking animation ── */
.thinking-pill {
    display: inline-flex; align-items: center; gap: 10px;
    background: rgba(255,255,255,0.04); backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.08); border-radius: 100px;
    padding: 8px 18px; box-shadow: 0 4px 20px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.05);
}
.thinking-pill span { font-size: 0.73rem; font-weight: 500; color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.1em; }
.tpulse { display: flex; gap: 5px; align-items: center; }
.tpulse i {
    width: 6px; height: 6px; border-radius: 50%; display: inline-block;
    background: linear-gradient(135deg, #6366f1, #a78bfa);
    animation: tpop 1.4s ease-in-out infinite both;
}
.tpulse i:nth-child(2) { animation-delay: 0.18s; }
.tpulse i:nth-child(3) { animation-delay: 0.36s; }
@keyframes tpop {
    0%, 80%, 100% { opacity: 0.2; transform: scale(0.7); }
    40% { opacity: 1; transform: scale(1); box-shadow: 0 0 8px rgba(99,102,241,0.6); }
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.13); }

/* ── Hide chrome ── */
#MainMenu, footer, header { visibility: hidden !important; height: 0 !important; }
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }
.stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [
    ("mode", "Home"),
    ("messages", []),
    ("pending_ocr_text", None),
    ("uploaded_file_name", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helper: navigate to a tool ────────────────────────────────────────────────
def go_to_tool(tool_name: str):
    st.session_state.mode = tool_name
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
    st.session_state.pending_ocr_text = None
    st.session_state.uploaded_file_name = None

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-mark">S</div>
        <h2>Spartan AI</h2>
        <p>Educational Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⌂  Home", key="sb_home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.session_state.pending_ocr_text = None
        st.session_state.uploaded_file_name = None
        st.rerun()

    st.markdown('<div class="sb-label">Tools</div>', unsafe_allow_html=True)

    for tool_name, meta in TOOL_META.items():
        if st.button(f"{meta['icon']}  {tool_name}", key=f"sb_{tool_name}"):
            go_to_tool(tool_name)
            st.rerun()

    st.markdown("""
    <div class="sb-foot">
        Senior Project<br>
        <span style="color: rgba(150,168,210,0.3);">Dallin Geurts &nbsp;·&nbsp; 2025</span>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Home":
    st.markdown("""
    <div style="text-align:center; padding: 56px 0 48px; position:relative; z-index:2;">
        <div class="home-kicker">Senior Project &nbsp;·&nbsp; 2025</div>
        <h1 class="home-h1">Education,<br><span class="grad">Reimagined.</span></h1>
        <p class="home-sub">
            Safe, powerful AI tools built for the modern classroom —
            from assignment generation to integrity checks,
            running privately and transparently.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # FIX: Render cards as clickable Streamlit buttons overlaid on styled HTML cards
    # by using columns instead of a pure-HTML grid (which can't call st.rerun).
    col1, col2 = st.columns(2)
    tool_items = list(TOOL_META.items())

    for idx, (name, meta) in enumerate(tool_items):
        col = col1 if idx % 2 == 0 else col2
        with col:
            st.markdown(f"""
            <div class="tool-card" style="--card-orb: {meta['orb']};">
                <div class="card-icon" style="color:{meta['accent']}; box-shadow:0 0 18px {meta['glow']};">
                    {meta['icon']}
                </div>
                <div class="card-name">{name}</div>
                <div class="card-desc">{meta['desc']}</div>
                <div class="card-arrow">→</div>
            </div>
            """, unsafe_allow_html=True)
            # Invisible button placed after card so it's clickable
            if st.button(f"Open {name}", key=f"home_card_{name}",
                         help=f"Open {name}",
                         use_container_width=True):
                go_to_tool(name)
                st.rerun()

    st.markdown("""
    <hr class="home-hr">
    <div class="home-footer">Spartan AI &nbsp;·&nbsp; Dallin Geurts &nbsp;·&nbsp; 2025</div>
    """, unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TOOL PAGE
# ══════════════════════════════════════════════════════════════════════════════
tool  = st.session_state.mode
model = MODEL_MAP[tool]
meta  = TOOL_META[tool]

# FIX: Removed unsupported `gap` parameter from st.columns()
col_hdr, col_btn = st.columns([7, 1.4])

with col_hdr:
    st.markdown(f"""
    <div class="tool-header" style="--orb:{meta['orb']};">
        <div class="th-icon" style="color:{meta['accent']}; box-shadow:0 0 20px {meta['glow']};">
            {meta['icon']}
        </div>
        <div>
            <p class="th-title">{tool}</p>
            <p class="th-desc">{meta['desc']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.markdown('<div class="nc-wrap" style="display:flex;align-items:center;height:100%;padding-top:8px;">', unsafe_allow_html=True)
    if st.button("＋ New chat", key="new_chat"):
        st.session_state.messages           = [{"role": "assistant", "content": "Hello! How can I help you today?"}]
        st.session_state.pending_ocr_text   = None
        st.session_state.uploaded_file_name = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Chat history ───────────────────────────────────────────────────────────────
# FIX: Always use display_text; fall back to content only for assistant messages
# that were stored before display_text existed (safe because assistant content
# is never the raw blob — only user messages carry the blob in `content`).
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg["content"]))

# ── File uploader ──────────────────────────────────────────────────────────────
# FIX: Show dependency warnings if libraries are missing
if not PyPDF2:
    st.warning("PyPDF2 not installed — PDF upload disabled.")
if not docx_module:
    st.warning("python-docx not installed — DOCX upload disabled.")
if not TESSERACT_OK:
    st.warning("pytesseract not installed — image OCR disabled.")

uploaded_file = st.file_uploader(
    "Attach a file — PDF, DOCX, TXT, or image (OCR supported)",
    type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "gif", "bmp", "tiff"],
)

# FIX: Guard against accessing .name on None; only process when a new file arrives
if uploaded_file is not None and uploaded_file.name != st.session_state.uploaded_file_name:
    with st.spinner("Reading file…"):
        extracted = ""
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        try:
            if ext == "pdf":
                if PyPDF2:
                    reader = PyPDF2.PdfReader(uploaded_file)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t:
                            extracted += t + "\n"
                else:
                    extracted = "(PyPDF2 not installed — cannot read PDF)"

            elif ext == "docx":
                if docx_module:
                    d = docx_module.Document(uploaded_file)   # FIX: use alias
                    for para in d.paragraphs:
                        extracted += para.text + "\n"
                else:
                    extracted = "(python-docx not installed — cannot read DOCX)"

            elif ext == "txt":
                extracted = uploaded_file.read().decode("utf-8", errors="ignore")

            elif ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]:
                if TESSERACT_OK:
                    img = Image.open(uploaded_file).convert("RGB")
                    extracted = pytesseract.image_to_string(img, config=OCR_CONFIG)
                else:
                    extracted = "(pytesseract not installed — cannot OCR image)"

            else:
                extracted = "(Unsupported file type)"

            extracted = extracted.strip() or "(No readable text found)"
            # FIX: Set pending_ocr_text AFTER successful extraction only
            st.session_state.pending_ocr_text   = extracted
            st.session_state.uploaded_file_name = uploaded_file.name
            st.success(f"✓  {uploaded_file.name} processed")

        except Exception as e:
            st.error(f"Could not read file: {e}")
            # FIX: Do NOT clear pending_ocr_text here — preserve any previously
            # loaded file text so the user doesn't lose their upload on a retry.

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Message Spartan AI…")

if user_input:
    # FIX: Capture and clear pending_ocr_text atomically before the API call
    ocr_text = st.session_state.pending_ocr_text
    if ocr_text:
        content = f"uploaded-file-text{{{ocr_text}}}\nuser-query{{{user_input}}}"
        st.session_state.pending_ocr_text   = None   # clear only after we've captured it
        st.session_state.uploaded_file_name = None
    else:
        content = f"user-query{{{user_input}}}"

    # Store user message: raw API content + clean display text (never show blob to user)
    st.session_state.messages.append({
        "role": "user",
        "content": content,
        "display_text": user_input,
    })
    with st.chat_message("user"):
        st.markdown(user_input)

    # ── Assistant turn ────────────────────────────────────────────────────────
    full_response = ""
    api_error     = False

    with st.chat_message("assistant"):
        thinking_slot = st.empty()
        resp_slot     = st.empty()

        thinking_slot.markdown("""
        <div class="thinking-pill">
            <div class="tpulse"><i></i><i></i><i></i></div>
            <span>Thinking</span>
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
                verify=False,   # SSL verification disabled (ngrok self-signed)
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
                        resp_slot.markdown(full_response + "▋", unsafe_allow_html=True)
                        time.sleep(0.01)
                resp_slot.markdown(full_response)
                thinking_slot.empty()

        except Exception as e:
            api_error = True
            thinking_slot.empty()
            full_response = ""   # ensure it stays empty string on error
            resp_slot.markdown(
                "<span style='font-size:0.85rem;color:rgba(252,129,74,0.8);'>"
                "⚠  Could not reach the server. Please try again."
                "</span>",
                unsafe_allow_html=True,
            )

    # FIX: Only append assistant message when there's actual content to save.
    # On error, full_response is "" — don't pollute history with empty messages.
    if full_response:
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "display_text": full_response,
        })
