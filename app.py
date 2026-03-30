import streamlit as st
import requests
import base64
import json
import re
import tempfile
import os
from PIL import Image
import pytesseract
import io

# ── Config ──────────────────────────────────────────────────────────────────
NGROK_URL        = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL  = f"{NGROK_URL}/api/chat"
OLLAMA_TAGS_URL  = f"{NGROK_URL}/api/tags"
USERNAME         = "dgeurts"
PASSWORD         = "thaidakar21"
OCR_CONFIG       = r"--oem 3 --psm 6"

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

TEXT_EXTENSIONS = {
    ".txt", ".js", ".ts", ".html", ".htm", ".css", ".py", ".java",
    ".c", ".cpp", ".h", ".cs", ".rb", ".go", ".rs", ".php", ".md",
    ".json", ".xml", ".yaml", ".yml", ".sh", ".sql",
}

# ── Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spartan AI",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@300;400;600;700&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #000 !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
}

/* Animated grid background */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,255,136,.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,.06) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
    animation: gridPulse 8s ease-in-out infinite;
}
@keyframes gridPulse {
    0%,100% { opacity:.6; }
    50%      { opacity:1; }
}

/* Scanline overlay */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,.15) 2px,
        rgba(0,0,0,.15) 4px
    );
    pointer-events: none;
    z-index: 1;
}

[data-testid="stMain"], .main, section[data-testid="stSidebar"] {
    background: transparent !important;
    position: relative;
    z-index: 2;
}

/* Hide default streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.stDeployButton { display: none; }
[data-testid="stDecoration"] { display: none !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(0,255,136,.05); }
::-webkit-scrollbar-thumb { background: rgba(0,255,136,.3); border-radius: 3px; }

/* ── Glass card ── */
.glass-card {
    background: rgba(0,255,136,.04);
    border: 1px solid rgba(0,255,136,.2);
    border-radius: 16px;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow:
        0 0 30px rgba(0,255,136,.05),
        inset 0 1px 0 rgba(0,255,136,.1);
    padding: 28px;
}

/* ── Hero / home ── */
.hero-title {
    font-family: 'Share Tech Mono', monospace;
    font-size: clamp(2.4rem, 6vw, 4.2rem);
    color: #00ff88;
    text-shadow: 0 0 20px rgba(0,255,136,.6), 0 0 60px rgba(0,255,136,.2);
    letter-spacing: .12em;
    animation: flicker 5s infinite;
}
@keyframes flicker {
    0%,95%,100% { opacity:1; }
    96%          { opacity:.85; }
    97%          { opacity:1; }
    98%          { opacity:.9; }
}
.hero-sub {
    font-size: 1.15rem;
    color: rgba(0,255,136,.65);
    letter-spacing: .06em;
    font-weight: 300;
}
.hero-desc {
    font-size: 1.05rem;
    color: rgba(0,255,136,.5);
    line-height: 1.7;
    max-width: 680px;
    margin: 0 auto;
}

/* ── Model cards ── */
.model-card {
    background: rgba(0,255,136,.04);
    border: 1px solid rgba(0,255,136,.18);
    border-radius: 14px;
    padding: 24px 20px;
    cursor: pointer;
    transition: all .25s ease;
    position: relative;
    overflow: hidden;
    min-height: 160px;
}
.model-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(0,255,136,.07) 0%, transparent 60%);
    opacity: 0;
    transition: opacity .25s;
}
.model-card:hover { border-color: rgba(0,255,136,.5); transform: translateY(-3px); box-shadow: 0 0 30px rgba(0,255,136,.12); }
.model-card:hover::before { opacity: 1; }
.model-icon { font-size: 2rem; margin-bottom: 10px; }
.model-name { font-family: 'Share Tech Mono', monospace; font-size: 1rem; color: #00ff88; letter-spacing:.06em; margin-bottom: 6px; }
.model-desc { font-size: .88rem; color: rgba(0,255,136,.5); line-height: 1.5; }

/* Status dot */
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    animation: statusPulse 2s infinite;
}
.status-dot.online  { background: #00ff88; box-shadow: 0 0 8px #00ff88; }
.status-dot.offline { background: #ff3355; box-shadow: 0 0 8px #ff3355; animation: none; }
@keyframes statusPulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
.status-label { font-family:'Share Tech Mono', monospace; font-size:.75rem; }
.status-label.online  { color: #00ff88; }
.status-label.offline { color: #ff3355; }

/* ── Chat page ── */
.chat-header {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.1rem;
    color: #00ff88;
    letter-spacing: .1em;
    padding: 14px 20px;
    background: rgba(0,255,136,.04);
    border-bottom: 1px solid rgba(0,255,136,.15);
    display: flex;
    align-items: center;
    gap: 12px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(20px);
}

/* ── Bubbles ── */
.bubble-row { display:flex; margin-bottom:18px; }
.bubble-row.user  { justify-content: flex-end; }
.bubble-row.ai    { justify-content: flex-start; }

.bubble {
    max-width: 70%;
    padding: 12px 18px;
    border-radius: 18px;
    font-size: .97rem;
    line-height: 1.6;
    position: relative;
    word-break: break-word;
}
.bubble.user {
    background: rgba(0,255,136,.12);
    border: 1px solid rgba(0,255,136,.3);
    border-bottom-right-radius: 4px;
    color: #e0ffe8;
    box-shadow: 0 0 20px rgba(0,255,136,.08);
}
.bubble.ai {
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(0,255,136,.15);
    border-bottom-left-radius: 4px;
    color: #c8ffd8;
    font-family: 'Share Tech Mono', monospace;
    font-size: .88rem;
    box-shadow: 0 0 20px rgba(0,255,136,.04);
}
.bubble.file-tag {
    max-width: 55%;
    padding: 7px 14px;
    font-size: .78rem;
    background: rgba(0,255,136,.07);
    border: 1px dashed rgba(0,255,136,.25);
    border-radius: 10px;
    color: rgba(0,255,136,.65);
    margin-top: 5px;
    font-family: 'Share Tech Mono', monospace;
}

/* Typing indicator */
.typing-dots {
    display:inline-flex; gap:4px; align-items:center; padding:4px 0;
}
.typing-dots span {
    width:6px; height:6px;
    background:#00ff88;
    border-radius:50%;
    animation: dot 1.2s infinite;
}
.typing-dots span:nth-child(2){ animation-delay:.2s; }
.typing-dots span:nth-child(3){ animation-delay:.4s; }
@keyframes dot { 0%,80%,100%{opacity:.2;transform:scale(.8);} 40%{opacity:1;transform:scale(1.2);} }

/* File download widget */
.file-widget {
    background: rgba(0,255,136,.07);
    border: 1px solid rgba(0,255,136,.3);
    border-radius: 12px;
    padding: 14px 18px;
    display: inline-flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    transition: all .2s;
    font-family: 'Share Tech Mono', monospace;
    font-size: .82rem;
    color: #00ff88;
}
.file-widget:hover { background: rgba(0,255,136,.13); box-shadow: 0 0 20px rgba(0,255,136,.15); }
.file-widget-icon { font-size: 1.3rem; }

/* ── Input bar ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(0,255,136,.05) !important;
    border: 1px solid rgba(0,255,136,.25) !important;
    border-radius: 12px !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important;
    caret-color: #00ff88 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(0,255,136,.6) !important;
    box-shadow: 0 0 20px rgba(0,255,136,.1) !important;
}

/* Buttons */
.stButton > button {
    background: rgba(0,255,136,.08) !important;
    border: 1px solid rgba(0,255,136,.3) !important;
    border-radius: 10px !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: .05em !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    background: rgba(0,255,136,.18) !important;
    border-color: rgba(0,255,136,.6) !important;
    box-shadow: 0 0 18px rgba(0,255,136,.2) !important;
    transform: translateY(-1px) !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(0,255,136,.04) !important;
    border: 1px dashed rgba(0,255,136,.25) !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] label { color: rgba(0,255,136,.6) !important; }

/* Divider */
.spartan-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,255,136,.3), transparent);
    margin: 20px 0;
}

/* Select box */
[data-testid="stSelectbox"] > div > div {
    background: rgba(0,255,136,.05) !important;
    border: 1px solid rgba(0,255,136,.2) !important;
    border-radius: 10px !important;
    color: #00ff88 !important;
}

/* Markdown text color override */
.stMarkdown p, .stMarkdown li, .stMarkdown h1,
.stMarkdown h2, .stMarkdown h3 { color: rgba(0,255,136,.75) !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def check_model_online(model_name: str) -> bool:
    try:
        r = requests.get(
            OLLAMA_TAGS_URL,
            auth=(USERNAME, PASSWORD),
            timeout=5,
        )
        if r.status_code == 200:
            tags = r.json().get("models", [])
            return any(t.get("name", "").startswith(model_name) for t in tags)
    except Exception:
        pass
    return False


def stream_chat(model: str, messages: list):
    """Yield text chunks from Ollama streaming API."""
    payload = {"model": model, "messages": messages, "stream": True}
    try:
        with requests.post(
            OLLAMA_CHAT_URL,
            auth=(USERNAME, PASSWORD),
            json=payload,
            stream=True,
            timeout=120,
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
    """
    Returns a list of dicts:
      {"type": "text",  "content": str}
      {"type": "file",  "filename": str, "ext": str, "content": str}
    """
    parts = []
    pos = 0
    pattern = re.compile(
        r'\[output-file-(\w+)-([^\]]+)\](.*?)\[/output-file-\1-\2\]',
        re.DOTALL
    )
    text_pattern = re.compile(
        r'\[output-text\](.*?)\[/output-text\]',
        re.DOTALL
    )

    # First pass: gather all spans
    spans = []
    for m in text_pattern.finditer(raw):
        spans.append(("text", m.start(), m.end(), m.group(1).strip(), None, None))
    for m in pattern.finditer(raw):
        ext, fname, content = m.group(1), m.group(2), m.group(3).strip()
        spans.append(("file", m.start(), m.end(), content, ext, fname))

    spans.sort(key=lambda x: x[1])

    for item in spans:
        kind = item[0]
        if kind == "text":
            parts.append({"type": "text", "content": item[3]})
        else:
            parts.append({"type": "file", "ext": item[4], "filename": item[5], "content": item[3]})

    # If no tags found, treat entire string as text
    if not parts and raw.strip():
        parts.append({"type": "text", "content": raw.strip()})

    return parts


def status_html(online: bool) -> str:
    cls = "online" if online else "offline"
    label = "ONLINE" if online else "OFFLINE"
    return (
        f'<span class="status-dot {cls}"></span>'
        f'<span class="status-label {cls}">{label}</span>'
    )


# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "page": "home",
        "active_model": None,
        "chat_history": [],     # list of {"role": "user"|"ai", "content": str, "file_label": str|None}
        "pending_file": None,   # {"label": str, "tag_content": str}
        "model_status": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# ── Refresh model statuses once per session load ──────────────────────────────
if not st.session_state.model_status:
    for display_name, model_id in MODEL_MAP.items():
        st.session_state.model_status[display_name] = check_model_online(model_id)


# ══════════════════════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_home():
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # Hero block
    st.markdown("""
    <div style='text-align:center; padding: 40px 20px 30px;'>
        <div style='font-family:"Share Tech Mono",monospace; font-size:.85rem;
                    color:rgba(0,255,136,.4); letter-spacing:.25em; margin-bottom:12px;'>
            ⚔ &nbsp; SYSTEM ONLINE &nbsp; ⚔
        </div>
        <div class='hero-title'>SPARTAN AI</div>
        <div style='margin-top:10px;' class='hero-sub'>
            Built by Dallin Geurts &nbsp;|&nbsp; Education Intelligence Platform
        </div>
        <div class='spartan-divider' style='max-width:400px; margin:24px auto;'></div>
        <div class='hero-desc'>
            Spartan AI is a suite of AI-powered tools designed to empower teachers and students.
            Generate assignments, grade submissions, detect AI-written content, and give students
            an intelligent learning companion — all from one unified platform.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Refresh status button
    col_r = st.columns([4, 1, 4])[1]
    with col_r:
        if st.button("↺ REFRESH STATUS", use_container_width=True):
            for display_name, model_id in MODEL_MAP.items():
                st.session_state.model_status[display_name] = check_model_online(model_id)
            st.rerun()

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # Model cards grid (2 columns)
    cols = st.columns(2, gap="large")
    for idx, (display_name, model_id) in enumerate(MODEL_MAP.items()):
        online = st.session_state.model_status.get(display_name, False)
        with cols[idx % 2]:
            status_h = status_html(online)
            st.markdown(f"""
            <div class='model-card glass-card'>
                <div class='model-icon'>{MODEL_ICONS[display_name]}</div>
                <div class='model-name'>{display_name.upper()}</div>
                <div class='model-desc'>{MODEL_DESCRIPTIONS[display_name]}</div>
                <div style='margin-top:14px;'>{status_h}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"LAUNCH →  {display_name}", key=f"launch_{idx}", use_container_width=True):
                st.session_state.page = "chat"
                st.session_state.active_model = display_name
                st.session_state.chat_history = []
                st.session_state.pending_file = None
                st.rerun()
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; font-family:"Share Tech Mono",monospace;
                font-size:.72rem; color:rgba(0,255,136,.25); letter-spacing:.15em;'>
        SPARTAN AI v1.0 &nbsp;|&nbsp; © DALLIN GEURTS &nbsp;|&nbsp; ALL SYSTEMS OPERATIONAL
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_chat():
    display_name = st.session_state.active_model
    model_id     = MODEL_MAP[display_name]
    online       = st.session_state.model_status.get(display_name, False)

    # ── Header ──
    status_h = status_html(online)
    st.markdown(f"""
    <div class='chat-header'>
        <span style='font-size:1.3rem'>{MODEL_ICONS[display_name]}</span>
        <span>{display_name.upper()}</span>
        <span style='margin-left:auto;'>{status_h}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Chat history area ──
    chat_area = st.container()
    with chat_area:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        for msg in st.session_state.chat_history:
            role = msg["role"]
            content = msg["content"]
            file_label = msg.get("file_label")

            if role == "user":
                st.markdown(f"""
                <div class='bubble-row user'>
                    <div>
                        <div class='bubble user'>{content}</div>
                        {f'<div style="display:flex;justify-content:flex-end;"><div class="bubble file-tag">📎 {file_label}</div></div>' if file_label else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            elif role == "ai":
                blocks = parse_output_blocks(content)
                block_html = ""
                for block in blocks:
                    if block["type"] == "text":
                        safe = block["content"].replace("\n", "<br>")
                        block_html += f"<div class='bubble ai'>{safe}</div>"
                    else:
                        # File widget — we encode content for download via a data URI
                        file_bytes = block["content"].encode("utf-8")
                        b64 = base64.b64encode(file_bytes).decode()
                        fname = block["filename"]
                        ext   = block["ext"]
                        mime  = "text/plain"
                        block_html += f"""
                        <div style='margin-top:6px;'>
                            <a href='data:{mime};base64,{b64}' download='{fname}.{ext}'
                               style='text-decoration:none;'>
                                <div class='file-widget'>
                                    <span class='file-widget-icon'>📄</span>
                                    <div>
                                        <div style='font-weight:700;'>{fname}.{ext}</div>
                                        <div style='opacity:.6;font-size:.72rem;'>Click to download generated file</div>
                                    </div>
                                    <span style='margin-left:auto;'>⬇</span>
                                </div>
                            </a>
                        </div>"""

                st.markdown(f"""
                <div class='bubble-row ai'>
                    <div style='max-width:75%;'>
                        {block_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:100px'></div>", unsafe_allow_html=True)

    # ── Fixed bottom input bar ──
    st.markdown("""
    <style>
    .input-dock {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        z-index: 999;
        background: rgba(0,0,0,.85);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border-top: 1px solid rgba(0,255,136,.15);
        padding: 14px 24px 18px;
    }
    </style>
    <div class='input-dock' id='input-dock'></div>
    """, unsafe_allow_html=True)

    # We use st.container positioned at bottom via the CSS trick
    with st.container():
        col_clear, col_input, col_file = st.columns([1, 8, 1])

        with col_clear:
            if st.button("🗑", help="Clear conversation & return home", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.pending_file = None
                st.session_state.page = "home"
                st.rerun()

        with col_input:
            user_text = st.chat_input(
                placeholder=f"Message {display_name}...",
            )

        with col_file:
            uploaded = st.file_uploader(
                "📎",
                label_visibility="collapsed",
                key="file_uploader",
            )

    # ── Process uploaded file ──
    if uploaded is not None:
        name = uploaded.name
        ext  = os.path.splitext(name)[1].lower()
        raw_bytes = uploaded.read()

        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}:
            ocr_text = extract_text_from_image(raw_bytes)
            tag_content = f"[input-file-image-text]\n{ocr_text}\n[/input-file-image-text]"
            label = f"{name} (OCR extracted)"
        elif ext in TEXT_EXTENSIONS:
            text = raw_bytes.decode("utf-8", errors="replace")
            ftype = ext.lstrip(".")
            tag_content = f"[input-file-{ftype}-text]\n{text}\n[/input-file-{ftype}-text]"
            label = f"{name}"
        else:
            tag_content = f"[input-file-binary]\n[File: {name} — unsupported type]\n[/input-file-binary]"
            label = f"{name} (unsupported)"

        st.session_state.pending_file = {"label": label, "tag_content": tag_content}

    # ── Handle send ──
    if user_text:
        file_label = None
        composed_user_message = f"[input-user-text]\n{user_text}\n[/input-user-text]"

        if st.session_state.pending_file:
            pf = st.session_state.pending_file
            file_label = pf["label"]
            composed_user_message = pf["tag_content"] + "\n\n" + composed_user_message
            st.session_state.pending_file = None

        # Add user bubble
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_text,
            "file_label": file_label,
        })

        # Build messages for Ollama
        ollama_messages = []
        system_prompt = (
            "You are Spartan AI, an intelligent assistant for teachers and students. "
            "You respond using the output format: [output-text]...[/output-text] for text responses "
            "and [output-file-<ext>-<filename>]...[/output-file-<ext>-<filename>] for generated files. "
            "Be helpful, precise, and educational."
        )
        ollama_messages.append({"role": "system", "content": system_prompt})

        for h in st.session_state.chat_history[:-1]:
            r = "user" if h["role"] == "user" else "assistant"
            content = h["content"]
            if h.get("file_label") and r == "user":
                content = h.get("_raw_content", content)
            ollama_messages.append({"role": r, "content": content})

        ollama_messages.append({"role": "user", "content": composed_user_message})

        # Store raw composed content for history replay
        st.session_state.chat_history[-1]["_raw_content"] = composed_user_message

        # Stream response
        with st.spinner(""):
            placeholder = st.empty()
            placeholder.markdown("""
            <div class='bubble-row ai'>
                <div class='bubble ai'>
                    <div class='typing-dots'>
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            full_response = ""
            for chunk in stream_chat(model_id, ollama_messages):
                full_response += chunk

            placeholder.empty()

        st.session_state.chat_history.append({
            "role": "ai",
            "content": full_response,
            "file_label": None,
        })
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "chat":
    render_chat()
