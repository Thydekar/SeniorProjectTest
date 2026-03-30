import streamlit as st
import requests
import base64
import json
import re
import os
import time
from PIL import Image
import pytesseract
import io

# ── Config ────────────────────────────────────────────────────────────────────
NGROK_URL       = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
OLLAMA_TAGS_URL = f"{NGROK_URL}/api/tags"
USERNAME        = "dgeurts"
PASSWORD        = "thaidakar21"
OCR_CONFIG      = r"--oem 3 --psm 6"

MODEL_MAP = {
    "Assignment Generation": "spartan-generator",
    "Assignment Grader":     "spartan-grader",
    "AI Content Detector":   "spartan-detector",
    "Student Chatbot":       "spartan-student",
}
MODEL_DESCRIPTIONS = {
    "Assignment Generation": "Generate custom assignments, quizzes, and exercises tailored to your curriculum.",
    "Assignment Grader":     "Automatically grade student submissions with detailed rubric-based feedback.",
    "AI Content Detector":   "Detect AI-generated content in student work with confidence scoring.",
    "Student Chatbot":       "An intelligent tutor that answers student questions and guides learning.",
}
MODEL_ICONS = {
    "Assignment Generation": "⚡",
    "Assignment Grader":     "📊",
    "AI Content Detector":   "🔍",
    "Student Chatbot":       "🎓",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
TEXT_EXTS  = {
    ".txt", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css",
    ".py", ".java", ".c", ".cpp", ".h", ".cs", ".rb", ".go", ".rs",
    ".php", ".md", ".json", ".xml", ".yaml", ".yml", ".sh", ".sql",
    ".swift", ".kt", ".r", ".m", ".pl", ".lua", ".dart",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spartan AI",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@300;400;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #000 !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
    overflow-x: hidden;
}

/* Animated grid */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0;
    background-image:
        linear-gradient(rgba(0,255,136,.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,.05) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none; z-index: 0;
    animation: gridPulse 8s ease-in-out infinite;
}
@keyframes gridPulse { 0%,100%{opacity:.5;} 50%{opacity:1;} }

/* Scanlines */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed; inset: 0;
    background: repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.12) 2px,rgba(0,0,0,.12) 4px);
    pointer-events: none; z-index: 1;
}

[data-testid="stMain"], .main { background: transparent !important; position: relative; z-index: 2; }
[data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: 100% !important; }

/* Hide chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"], .stDeployButton, [data-testid="stDecoration"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: rgba(0,255,136,.03); }
::-webkit-scrollbar-thumb { background: rgba(0,255,136,.25); border-radius: 3px; }

/* ── TOP NAV ── */
.spartan-nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 500;
    height: 52px;
    background: rgba(0,0,0,.8);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-bottom: 1px solid rgba(0,255,136,.12);
    display: flex; align-items: center; padding: 0 28px; gap: 20px;
}
.nav-brand {
    font-family: 'Share Tech Mono', monospace;
    font-size: .95rem; color: #00ff88;
    letter-spacing: .18em;
    text-shadow: 0 0 12px rgba(0,255,136,.5);
    margin-right: 12px; white-space: nowrap;
}
.nav-btn {
    font-family: 'Share Tech Mono', monospace;
    font-size: .72rem; color: rgba(0,255,136,.55);
    letter-spacing: .1em;
    padding: 5px 12px;
    border: 1px solid rgba(0,255,136,.15);
    border-radius: 6px;
    cursor: pointer;
    background: transparent;
    transition: all .2s;
    white-space: nowrap;
    text-decoration: none;
}
.nav-btn:hover, .nav-btn.active {
    color: #00ff88;
    border-color: rgba(0,255,136,.4);
    background: rgba(0,255,136,.07);
    box-shadow: 0 0 12px rgba(0,255,136,.1);
}
.nav-status {
    margin-left: auto;
    display: flex; align-items: center; gap: 6px;
    font-family: 'Share Tech Mono', monospace;
    font-size: .7rem;
}

/* Status dot */
.sdot {
    display: inline-block; width: 7px; height: 7px;
    border-radius: 50%;
}
.sdot.on  { background: #00ff88; box-shadow: 0 0 7px #00ff88; animation: pulse 2s infinite; }
.sdot.off { background: #ff3355; box-shadow: 0 0 7px #ff3355; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.35;} }

/* ── HERO ── */
.hero-wrap { text-align: center; padding: 80px 20px 40px; }
.hero-badge {
    font-family: 'Share Tech Mono', monospace;
    font-size: .75rem; color: rgba(0,255,136,.4);
    letter-spacing: .3em; margin-bottom: 14px;
}
.hero-title {
    font-family: 'Share Tech Mono', monospace;
    font-size: clamp(2.6rem,7vw,5rem);
    color: #00ff88;
    text-shadow: 0 0 24px rgba(0,255,136,.6), 0 0 80px rgba(0,255,136,.15);
    letter-spacing: .14em;
    animation: flicker 6s infinite;
}
@keyframes flicker { 0%,94%,100%{opacity:1;} 95%{opacity:.8;} 97%{opacity:.95;} 98%{opacity:.82;} }
.hero-sub { font-size: 1.1rem; color: rgba(0,255,136,.55); letter-spacing:.07em; margin-top:8px; }
.hero-line { height:1px; background:linear-gradient(90deg,transparent,rgba(0,255,136,.3),transparent); max-width:500px; margin:22px auto; }
.hero-desc { font-size:1rem; color:rgba(0,255,136,.45); line-height:1.8; max-width:640px; margin:0 auto; }

/* ── MODEL CARDS ── */
.model-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:18px; padding:0 24px 40px; max-width:900px; margin:0 auto; }
.mcard {
    background: rgba(0,255,136,.03);
    border: 1px solid rgba(0,255,136,.14);
    border-radius: 14px; padding: 22px 20px;
    position: relative; overflow: hidden;
    transition: all .25s;
    min-height: 150px;
}
.mcard::before {
    content:''; position:absolute; inset:0;
    background:linear-gradient(135deg,rgba(0,255,136,.06) 0%,transparent 55%);
    opacity:0; transition:opacity .25s;
}
.mcard:hover { border-color:rgba(0,255,136,.4); transform:translateY(-3px); box-shadow:0 0 28px rgba(0,255,136,.1); }
.mcard:hover::before { opacity:1; }
.mcard-icon { font-size:1.8rem; margin-bottom:8px; }
.mcard-name { font-family:'Share Tech Mono',monospace; font-size:.9rem; color:#00ff88; letter-spacing:.06em; margin-bottom:5px; }
.mcard-desc { font-size:.84rem; color:rgba(0,255,136,.45); line-height:1.5; margin-bottom:14px; }
.mcard-status { display:flex; align-items:center; gap:6px; font-family:'Share Tech Mono',monospace; font-size:.7rem; }

/* ── GLASS BUTTON ── */
.stButton > button {
    background: rgba(0,255,136,.07) !important;
    border: 1px solid rgba(0,255,136,.28) !important;
    border-radius: 9px !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important; font-size:.9rem !important;
    letter-spacing: .05em !important;
    transition: all .2s !important;
    padding: 6px 14px !important;
}
.stButton > button:hover {
    background: rgba(0,255,136,.15) !important;
    border-color: rgba(0,255,136,.55) !important;
    box-shadow: 0 0 18px rgba(0,255,136,.18) !important;
    transform: translateY(-1px) !important;
}

/* ── CHAT LAYOUT ── */
/* The chat scroll area sits between the fixed nav (52px) and fixed dock (70px) */
.chat-scroll-area {
    position: fixed;
    top: 52px; bottom: 70px;
    left: 0; right: 0;
    overflow-y: auto;
    padding: 20px 0 8px;
    z-index: 10;
}
.chat-inner { max-width: 860px; margin: 0 auto; padding: 0 20px; }

/* ── BUBBLES ── */
.brow { display:flex; margin-bottom:14px; }
.brow.user { justify-content:flex-end; }
.brow.ai   { justify-content:flex-start; }

.bubble {
    max-width: 68%;
    padding: 11px 16px;
    border-radius: 18px;
    font-size: .95rem;
    line-height: 1.65;
    word-break: break-word;
    position: relative;
}
.bubble.user {
    background: rgba(0,255,136,.1);
    border: 1px solid rgba(0,255,136,.28);
    border-bottom-right-radius: 4px;
    color: #ddfff0;
    box-shadow: 0 0 18px rgba(0,255,136,.07);
}
.bubble.ai {
    background: rgba(255,255,255,.035);
    border: 1px solid rgba(0,255,136,.12);
    border-bottom-left-radius: 4px;
    color: #c8ffd8;
    font-family: 'Share Tech Mono', monospace;
    font-size: .84rem;
    box-shadow: 0 0 18px rgba(0,255,136,.04);
    white-space: pre-wrap;
}
.bubble.file-pill {
    max-width: 56%;
    padding: 6px 13px;
    font-size: .75rem;
    background: rgba(0,255,136,.06);
    border: 1px dashed rgba(0,255,136,.22);
    border-radius: 9px;
    color: rgba(0,255,136,.6);
    margin-top: 4px;
    font-family: 'Share Tech Mono', monospace;
}

/* Typing dots */
.tdots { display:inline-flex; gap:5px; align-items:center; padding:2px 0; }
.tdots span {
    width:6px; height:6px; background:#00ff88; border-radius:50%;
    animation: td 1.1s infinite;
}
.tdots span:nth-child(2){animation-delay:.18s;}
.tdots span:nth-child(3){animation-delay:.36s;}
@keyframes td { 0%,80%,100%{opacity:.2;transform:scale(.75);} 40%{opacity:1;transform:scale(1.15);} }

/* Typing cursor */
.cursor {
    display:inline-block;
    width:2px; height:1em;
    background:#00ff88;
    margin-left:2px;
    vertical-align:text-bottom;
    animation:blink .7s step-end infinite;
}
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0;} }

/* File download widget */
.file-widget {
    display:inline-flex; align-items:center; gap:10px;
    background: rgba(0,255,136,.06);
    border: 1px solid rgba(0,255,136,.25);
    border-radius: 11px; padding: 11px 16px;
    text-decoration:none; color:#00ff88;
    font-family:'Share Tech Mono',monospace; font-size:.78rem;
    transition:all .2s; margin-top:5px;
}
.file-widget:hover {
    background:rgba(0,255,136,.12);
    box-shadow:0 0 22px rgba(0,255,136,.15);
}
.file-widget-icon { font-size:1.2rem; }
.file-gen-badge {
    display:inline-flex; align-items:center; gap:8px;
    background: rgba(0,255,136,.05);
    border: 1px dashed rgba(0,255,136,.2);
    border-radius:9px; padding:10px 14px;
    font-family:'Share Tech Mono',monospace; font-size:.75rem;
    color:rgba(0,255,136,.55); margin-top:5px;
    animation: genpulse 1.5s infinite;
}
@keyframes genpulse { 0%,100%{opacity:.5;} 50%{opacity:1;} }

/* ── FIXED INPUT DOCK ── */
.input-dock {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    height: 70px;
    background: rgba(0,0,0,.88);
    backdrop-filter: blur(28px);
    -webkit-backdrop-filter: blur(28px);
    border-top: 1px solid rgba(0,255,136,.13);
    z-index: 400;
    display: flex; align-items: center;
    padding: 0 16px; gap: 10px;
}

/* Icon buttons in dock */
.dock-icon-btn {
    flex-shrink: 0;
    width: 42px; height: 42px;
    border-radius: 10px;
    border: 1px solid rgba(0,255,136,.25);
    background: rgba(0,255,136,.06);
    color: #00ff88;
    font-size: 1.05rem;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; transition: all .2s;
}
.dock-icon-btn:hover {
    background: rgba(0,255,136,.15);
    border-color: rgba(0,255,136,.5);
    box-shadow: 0 0 14px rgba(0,255,136,.18);
}

/* Override chat_input to be zero-margin */
[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 14px !important;
    left: 70px !important;
    right: 70px !important;
    z-index: 450 !important;
    margin: 0 !important;
}
[data-testid="stChatInput"] > div {
    background: rgba(0,255,136,.05) !important;
    border: 1px solid rgba(0,255,136,.22) !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important;
    caret-color: #00ff88 !important;
}
[data-testid="stChatInput"] button {
    color: #00ff88 !important;
}

/* File upload widget hide default label */
[data-testid="stFileUploader"] section { padding: 0 !important; }
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
    display: none !important;
}
[data-testid="stFileUploader"] .uploadedFile { display: none !important; }

/* Pending file pill shown inside dock */
.pending-pill {
    position: fixed;
    bottom: 74px; right: 16px;
    background: rgba(0,255,136,.08);
    border: 1px solid rgba(0,255,136,.25);
    border-radius: 9px;
    padding: 6px 12px;
    font-family: 'Share Tech Mono', monospace;
    font-size: .72rem;
    color: rgba(0,255,136,.7);
    display: flex; align-items: center; gap:8px;
    z-index: 450;
}

/* Text inputs */
.stTextInput > div > div > input {
    background: rgba(0,255,136,.05) !important;
    border: 1px solid rgba(0,255,136,.2) !important;
    border-radius: 10px !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
}

/* Markdown override */
.stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: rgba(0,255,136,.7) !important;
}

/* Padding for page body below fixed nav */
.page-body { padding-top: 62px; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def check_model_online(model_name: str) -> bool:
    try:
        r = requests.get(OLLAMA_TAGS_URL, auth=(USERNAME, PASSWORD), timeout=5)
        if r.status_code == 200:
            tags = r.json().get("models", [])
            return any(t.get("name", "").startswith(model_name) for t in tags)
    except Exception:
        pass
    return False


def stream_chat(model: str, messages: list):
    payload = {"model": model, "messages": messages, "stream": True}
    try:
        with requests.post(
            OLLAMA_CHAT_URL, auth=(USERNAME, PASSWORD),
            json=payload, stream=True, timeout=120,
        ) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"\n[ERROR: {e}]"


def extract_text_from_image(file_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img, config=OCR_CONFIG)
    except Exception as e:
        return f"[OCR failed: {e}]"


def parse_output_blocks(raw: str):
    parts = []
    text_pattern = re.compile(r'\[output-text\](.*?)\[/output-text\]', re.DOTALL)
    file_pattern  = re.compile(r'\[output-file-(\w+)-([^\]]+)\](.*?)\[/output-file-\1-\2\]', re.DOTALL)

    spans = []
    for m in text_pattern.finditer(raw):
        spans.append(("text", m.start(), m.end(), m.group(1).strip(), None, None))
    for m in file_pattern.finditer(raw):
        spans.append(("file", m.start(), m.end(), m.group(3).strip(), m.group(1), m.group(2)))
    spans.sort(key=lambda x: x[1])

    for item in spans:
        if item[0] == "text":
            parts.append({"type": "text", "content": item[3]})
        else:
            parts.append({"type": "file", "ext": item[4], "filename": item[5], "content": item[3]})

    if not parts and raw.strip():
        parts.append({"type": "text", "content": raw.strip()})
    return parts


def status_html(online: bool, label: bool = True) -> str:
    cls   = "on" if online else "off"
    lbl   = "ONLINE" if online else "OFFLINE"
    color = "#00ff88" if online else "#ff3355"
    lbl_html = f'<span style="color:{color};font-family:\'Share Tech Mono\',monospace;font-size:.7rem;">{lbl}</span>' if label else ""
    return f'<span class="sdot {cls}"></span>{lbl_html}'


def build_ollama_messages(chat_history: list, model_display: str) -> list:
    system_prompt = (
        f"You are Spartan AI — specifically the {model_display} module. "
        "You are an intelligent assistant for teachers and students. "
        "Always respond using the output format: [output-text]...[/output-text] for text, "
        "and [output-file-<ext>-<filename>]...[/output-file-<ext>-<filename>] for generated files. "
        "Be helpful, precise, and educational."
    )
    msgs = [{"role": "system", "content": system_prompt}]
    for h in chat_history:
        r = "user" if h["role"] == "user" else "assistant"
        msgs.append({"role": r, "content": h.get("_raw", h["content"])})
    return msgs


# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "page":          "home",
        "active_model":  None,
        "chat_history":  [],
        "pending_file":  None,   # {"label": str, "tag": str}
        "model_status":  {},
        "upload_key":    0,      # increment to reset file uploader
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Check statuses once per session
if not st.session_state.model_status:
    for dname, mid in MODEL_MAP.items():
        st.session_state.model_status[dname] = check_model_online(mid)


# ── Navigation bar (always rendered) ─────────────────────────────────────────
def render_nav():
    active = st.session_state.page
    active_model = st.session_state.active_model or ""

    nav_items_html = ""
    for dname in MODEL_MAP:
        is_active = (active == "chat" and active_model == dname)
        cls = "nav-btn active" if is_active else "nav-btn"
        icon = MODEL_ICONS[dname]
        nav_items_html += f'<span class="{cls}" id="nav_{dname.replace(" ","_")}">{icon} {dname}</span>'

    st.markdown(f"""
    <div class="spartan-nav">
        <span class="nav-brand">⚔ SPARTAN AI</span>
        <div style="width:1px;height:26px;background:rgba(0,255,136,.15);"></div>
        {nav_items_html}
        <div class="nav-status">
            <span style="color:rgba(0,255,136,.35);font-size:.65rem;letter-spacing:.1em;">SYSTEMS</span>
            <span class="sdot on"></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Render invisible Streamlit buttons for nav clicks
    cols = st.columns(len(MODEL_MAP) + 1)
    with cols[0]:
        if st.button("🏠 Home", key="nav_home_btn", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    for i, dname in enumerate(MODEL_MAP):
        with cols[i + 1]:
            if st.button(f"{MODEL_ICONS[dname]} {dname}", key=f"nav_{i}", use_container_width=True):
                st.session_state.page = "chat"
                st.session_state.active_model = dname
                # Don't reset history when switching via nav
                st.session_state.pending_file = None
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_home():
    st.markdown('<div class="page-body">', unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-badge">⚔ &nbsp; EDUCATION INTELLIGENCE PLATFORM &nbsp; ⚔</div>
        <div class="hero-title">SPARTAN AI</div>
        <div class="hero-sub">Built by Dallin Geurts &nbsp;·&nbsp; Empowering Teachers & Students</div>
        <div class="hero-line"></div>
        <div class="hero-desc">
            A suite of specialized AI tools designed to streamline every aspect of education —
            from generating custom assignments to grading, detecting AI-written content,
            and giving every student an intelligent personal tutor.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Refresh
    rc = st.columns([5, 2, 5])
    with rc[1]:
        if st.button("↺  Refresh Status", use_container_width=True):
            for dn, mid in MODEL_MAP.items():
                st.session_state.model_status[dn] = check_model_online(mid)
            st.rerun()

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # Model cards
    cols = st.columns(2, gap="large")
    for idx, (dname, mid) in enumerate(MODEL_MAP.items()):
        online = st.session_state.model_status.get(dname, False)
        with cols[idx % 2]:
            s_html = status_html(online)
            st.markdown(f"""
            <div class="mcard">
                <div class="mcard-icon">{MODEL_ICONS[dname]}</div>
                <div class="mcard-name">{dname.upper()}</div>
                <div class="mcard-desc">{MODEL_DESCRIPTIONS[dname]}</div>
                <div class="mcard-status">{s_html}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Launch {dname} →", key=f"home_launch_{idx}", use_container_width=True):
                st.session_state.page = "chat"
                st.session_state.active_model = dname
                st.session_state.chat_history = []
                st.session_state.pending_file = None
                st.rerun()
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center;font-family:"Share Tech Mono",monospace;
                font-size:.68rem;color:rgba(0,255,136,.2);letter-spacing:.15em;'>
        SPARTAN AI v1.0 &nbsp;|&nbsp; © DALLIN GEURTS
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_chat():
    display_name = st.session_state.active_model
    model_id     = MODEL_MAP[display_name]
    online       = st.session_state.model_status.get(display_name, False)
    s_html       = status_html(online)

    # ── Scrollable chat area (CSS-positioned, above dock) ──
    # We render messages inside a fixed div via HTML
    history = st.session_state.chat_history

    # Build all bubble HTML
    bubbles_html = ""
    for msg in history:
        role      = msg["role"]
        content   = msg["content"]
        file_lbl  = msg.get("file_label")

        if role == "user":
            safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            pill = ""
            if file_lbl:
                safe_lbl = file_lbl.replace("&", "&amp;").replace("<", "&lt;")
                pill = f'<div style="display:flex;justify-content:flex-end;margin-top:4px;"><div class="bubble file-pill">📎 {safe_lbl}</div></div>'
            bubbles_html += f"""
            <div class="brow user">
                <div>
                    <div class="bubble user">{safe}</div>
                    {pill}
                </div>
            </div>"""

        elif role == "ai":
            blocks = parse_output_blocks(content)
            inner  = ""
            for block in blocks:
                if block["type"] == "text":
                    safe = block["content"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                    inner += f'<div class="bubble ai">{safe}</div>'
                else:
                    raw_bytes = block["content"].encode("utf-8")
                    b64       = base64.b64encode(raw_bytes).decode()
                    fname     = block["filename"]
                    ext       = block["ext"]
                    inner += f"""
                    <a href="data:text/plain;base64,{b64}" download="{fname}.{ext}" style="text-decoration:none;">
                        <div class="file-widget">
                            <span class="file-widget-icon">📄</span>
                            <div>
                                <div style="font-weight:700;">{fname}.{ext}</div>
                                <div style="opacity:.55;font-size:.68rem;">Click to download</div>
                            </div>
                            <span style="margin-left:16px;">⬇</span>
                        </div>
                    </a>"""
            bubbles_html += f'<div class="brow ai"><div style="max-width:72%;">{inner}</div></div>'

    # Auto-scroll JS
    scroll_js = """
    <script>
    (function(){
        var el = document.getElementById('chat-scroll');
        if(el) el.scrollTop = el.scrollHeight;
    })();
    </script>"""

    # Pending file pill
    pf = st.session_state.pending_file
    pending_pill_html = ""
    if pf:
        lbl = pf["label"].replace("&","&amp;").replace("<","&lt;")
        pending_pill_html = f"""
        <div class="pending-pill">
            📎 <span>{lbl}</span>
            <span style="color:rgba(0,255,136,.4);cursor:pointer;" id="clear-pill">✕</span>
        </div>"""

    st.markdown(f"""
    {pending_pill_html}
    <div id="chat-scroll" class="chat-scroll-area">
        <div class="chat-inner">
            {bubbles_html}
            <div id="chat-bottom" style="height:8px;"></div>
        </div>
    </div>
    {scroll_js}
    """, unsafe_allow_html=True)

    # ── Fixed dock: rendered via columns trick ──
    # We use streamlit's native elements, styled to appear as the dock
    # Position clear btn on far left, file btn on far right, chat_input fills middle

    # Left: New Chat / Clear button
    btn_col, _, file_col = st.columns([1, 14, 1])

    with btn_col:
        if st.button("🗑", key="clear_chat", help="New chat", use_container_width=True):
            st.session_state.chat_history  = []
            st.session_state.pending_file  = None
            st.session_state.upload_key   += 1
            st.rerun()

    # Center: chat input (Streamlit places this at bottom automatically)
    user_text = st.chat_input(placeholder=f"Message {display_name}...")

    # Right: file upload (hidden dropzone, only browse button)
    with file_col:
        uploaded = st.file_uploader(
            "📎",
            key=f"fu_{st.session_state.upload_key}",
            label_visibility="collapsed",
            type=[
                # images
                "png","jpg","jpeg","gif","bmp","tiff","webp",
                # text types
                "txt","js","ts","jsx","tsx","html","htm","css",
                "py","java","c","cpp","h","cs","rb","go","rs",
                "php","md","json","xml","yaml","yml","sh","sql",
                "swift","kt","r","m","pl","lua","dart",
            ],
        )

    # Process newly uploaded file
    if uploaded is not None and (
        pf is None or pf.get("_fname") != uploaded.name
    ):
        name = uploaded.name
        ext  = os.path.splitext(name)[1].lower()
        raw_bytes = uploaded.read()

        if ext in IMAGE_EXTS:
            ocr_text    = extract_text_from_image(raw_bytes)
            tag_content = f"[input-file-image-text]\n{ocr_text}\n[/input-file-image-text]"
            label       = f"{name} (image→OCR)"
        else:
            text        = raw_bytes.decode("utf-8", errors="replace")
            ftype       = ext.lstrip(".") or "txt"
            tag_content = f"[input-file-{ftype}-text]\n{text}\n[/input-file-{ftype}-text]"
            label       = name

        st.session_state.pending_file = {
            "label":  label,
            "tag":    tag_content,
            "_fname": name,
        }
        st.rerun()

    # ── Handle message send ──
    if user_text:
        pf = st.session_state.pending_file
        file_label = None
        composed   = f"[input-user-text]\n{user_text}\n[/input-user-text]"

        if pf:
            file_label  = pf["label"]
            composed    = pf["tag"] + "\n\n" + composed
            # Clear pending file and reset uploader key so it disappears
            st.session_state.pending_file = None
            st.session_state.upload_key  += 1

        # Append user message
        st.session_state.chat_history.append({
            "role":       "user",
            "content":    user_text,
            "file_label": file_label,
            "_raw":       composed,
        })

        # Build Ollama message list
        ollama_msgs = build_ollama_messages(
            st.session_state.chat_history, display_name
        )

        # Stream the response, showing live typing
        full_response = ""
        typing_placeholder = st.empty()

        # Show typing indicator as first frame
        typing_placeholder.markdown("""
        <div class="brow ai" style="padding:0 20px;max-width:860px;margin:0 auto;">
            <div class="bubble ai"><div class="tdots"><span></span><span></span><span></span></div></div>
        </div>
        """, unsafe_allow_html=True)

        for chunk in stream_chat(model_id, ollama_msgs):
            full_response += chunk
            # Show growing response with cursor
            # Strip tags for live display, show raw while streaming
            display_text = full_response.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            typing_placeholder.markdown(f"""
            <div class="brow ai" style="padding:0 20px;max-width:860px;margin:0 auto;">
                <div class="bubble ai">{display_text}<span class="cursor"></span></div>
            </div>
            """, unsafe_allow_html=True)

        typing_placeholder.empty()

        # Save completed AI message
        st.session_state.chat_history.append({
            "role":    "ai",
            "content": full_response,
        })
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
render_nav()

if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "chat":
    render_chat()
