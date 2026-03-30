import streamlit as st
import requests
import json
import base64
import html as html_lib
import re
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
NGROK_URL       = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
OLLAMA_TAGS_URL = f"{NGROK_URL}/api/tags"
USERNAME        = "dgeurts"
PASSWORD        = "thaidakar21"
OCR_CONFIG      = r"--oem 3 --psm 6"
AUTH            = (USERNAME, PASSWORD)

MODEL_MAP = {
    "Assignment Generation": "spartan-generator",
    "Assignment Grader":     "spartan-grader",
    "AI Content Detector":   "spartan-detector",
    "Student Chatbot":       "spartan-student",
}
MODEL_ICONS = {
    "Assignment Generation": "📝",
    "Assignment Grader":     "✅",
    "AI Content Detector":   "🔍",
    "Student Chatbot":       "🎓",
}
MODEL_DESC = {
    "Assignment Generation": "Generate custom assignments, rubrics, and worksheets tailored to your curriculum.",
    "Assignment Grader":     "Grade student submissions with detailed, consistent, and fair feedback.",
    "AI Content Detector":   "Detect AI-generated content in student work with confidence scoring.",
    "Student Chatbot":       "A guided learning assistant that helps students understand concepts.",
}

TEXT_EXTENSIONS = {
    ".txt",".js",".ts",".jsx",".tsx",".html",".htm",".css",
    ".py",".java",".c",".cpp",".h",".cs",".go",".rb",".php",
    ".json",".xml",".yaml",".yml",".md",".csv",".sql",".sh",
    ".bash",".r",".swift",".kt",".rs",".dart",".vue",".svelte",
}
IMAGE_EXTENSIONS = {".png",".jpg",".jpeg",".bmp",".tiff",".tif",".gif",".webp"}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spartan AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Pure helpers ──────────────────────────────────────────────────────────────

def check_model_online(model_name: str) -> bool:
    try:
        r = requests.get(OLLAMA_TAGS_URL, auth=AUTH, timeout=5)
        if r.status_code == 200:
            names = [t.get("name", "").split(":")[0] for t in r.json().get("models", [])]
            return model_name in names
    except Exception:
        pass
    return False


def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img, config=OCR_CONFIG)
    except Exception as e:
        return f"[OCR error: {e}]"


def build_user_content(text: str, file_info) -> str:
    parts = []
    if file_info:
        ext  = file_info["ext"]
        body = file_info["body"]
        tag  = "image" if ext in IMAGE_EXTENSIONS else ext.lstrip(".")
        parts.append(f"[input-file-{tag}-text]\n{body}\n[/input-file-{tag}-text]")
    parts.append(f"[input-user-text]\n{text}\n[/input-user-text]")
    return "\n".join(parts)


def stream_chat(model_name: str, messages: list):
    payload = {"model": model_name, "messages": messages, "stream": True}
    with requests.post(OLLAMA_CHAT_URL, auth=AUTH, json=payload, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            try:
                chunk = json.loads(raw)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
            except json.JSONDecodeError:
                continue


def _strip_tags(s: str) -> str:
    """Remove all protocol bracket-tags from a string."""
    s = re.sub(r'\[/?output-text\]', '', s)
    s = re.sub(r'\[/?input-[^\]]+\]', '', s)
    s = re.sub(r'\[output-file-[^\]]+\]', '', s)
    s = re.sub(r'\[/output-file-[^\]]+\]', '', s)
    return s.strip()


def parse_output(raw: str) -> list:
    """
    Split raw AI response into typed segments.
    All protocol tags are stripped; text content is always clean.
    Returns: list of {"type": "text"|"file", ...}
    """
    file_pat = re.compile(
        r'\[output-file-([a-zA-Z0-9]+)-([^\]]+)\](.*?)\[/output-file-\1-\2\]',
        re.DOTALL,
    )
    text_pat = re.compile(r'\[output-text\](.*?)\[/output-text\]', re.DOTALL)

    all_matches = sorted(
        list(file_pat.finditer(raw)) + list(text_pat.finditer(raw)),
        key=lambda m: m.start(),
    )

    segments, last = [], 0
    for m in all_matches:
        before = _strip_tags(raw[last : m.start()])
        if before:
            segments.append({"type": "text", "content": before})

        if m.lastindex == 3:  # file block
            segments.append({
                "type":     "file",
                "filetype": m.group(1),
                "filename": m.group(2),
                "content":  m.group(3).strip(),
            })
        else:  # output-text block
            txt = _strip_tags(m.group(1))
            if txt:
                segments.append({"type": "text", "content": txt})

        last = m.end()

    tail = _strip_tags(raw[last:])
    if tail:
        segments.append({"type": "text", "content": tail})

    if not segments:
        segments.append({"type": "text", "content": _strip_tags(raw) or raw})

    return segments


def safe_html(text: str) -> str:
    return html_lib.escape(str(text)).replace("\n", "<br>")


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

:root {
    --green:       #00ff88;
    --green-dim:   #00cc6a;
    --green-glow:  rgba(0,255,136,0.18);
    --red:         #ff4455;
    --glass-bg:    rgba(8,18,12,0.80);
    --glass-bdr:   rgba(0,255,136,0.14);
    --glass-shine: rgba(255,255,255,0.03);
    --bg:          #020a05;
    --text:        #c8ffe0;
    --text-dim:    #4a7560;
    --mono:        'Share Tech Mono', monospace;
    --sans:        'Rajdhani', sans-serif;
}

/* Base */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}

/* Grid bg */
[data-testid="stAppViewContainer"]::before {
    content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
    background-image:
        linear-gradient(rgba(0,255,136,0.032) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,0.032) 1px, transparent 1px);
    background-size: 44px 44px;
}
/* Scanlines */
[data-testid="stAppViewContainer"]::after {
    content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 2px,
        rgba(0,0,0,0.045) 2px, rgba(0,0,0,0.045) 4px);
}
[data-testid="stMain"] { background:transparent !important; position:relative; z-index:1; }

/* Strip Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"] { display:none !important; }

.block-container { padding:0 !important; max-width:100% !important; }
[data-testid="stMainBlockContainer"] { padding:0 !important; }

/* Scrollbar */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(0,255,136,0.16); border-radius:2px; }

/* ── HOME ── */
.home-wrap { padding:3rem 2rem 2rem; max-width:860px; margin:0 auto; }
.home-logo {
    font-family: var(--mono);
    font-size: 3rem;
    color: var(--green);
    text-shadow: 0 0 24px var(--green), 0 0 60px rgba(0,255,136,0.25);
    letter-spacing: 0.1em;
    text-align: center;
}
.home-byline {
    font-family: var(--mono); font-size: 0.68rem;
    color: var(--text-dim); letter-spacing: 0.28em;
    text-transform: uppercase; text-align: center; margin-top:0.45rem;
}
.home-desc {
    font-family: var(--sans); font-size: 1rem;
    color: rgba(200,255,224,0.72); text-align:center;
    max-width: 540px; margin: 1.5rem auto 0; line-height:1.75;
}
hr.div { border:none; border-top:1px solid var(--glass-bdr); margin:2rem 0 1.6rem; }
.sec-label {
    font-family:var(--mono); font-size:0.66rem; color:var(--text-dim);
    letter-spacing:0.3em; text-transform:uppercase; text-align:center; margin-bottom:1.3rem;
}

/* ── Model cards ── */
.model-card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-bdr);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border-radius: 14px;
    padding: 1.2rem 1.1rem 1rem;
    position: relative; overflow:hidden;
    box-shadow: 0 4px 22px rgba(0,0,0,0.5), 0 0 0 1px var(--glass-shine) inset;
    margin-bottom: 0.35rem;
}
.model-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:1px;
    background: linear-gradient(90deg,transparent,var(--green),transparent); opacity:0.35;
}
.card-icon { font-size:1.6rem; line-height:1; margin-bottom:0.4rem; }
.card-title {
    font-family:var(--sans); font-weight:700; font-size:1rem;
    color:var(--green); letter-spacing:0.04em; margin-bottom:0.25rem;
}
.card-desc { font-family:var(--sans); font-size:0.84rem; color:var(--text-dim); line-height:1.5; }
.card-status {
    display:flex; align-items:center; gap:6px;
    margin-top:0.8rem; font-family:var(--mono); font-size:0.7rem;
}
.dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.dot.on  { background:var(--green); box-shadow:0 0 5px var(--green); }
.dot.off { background:var(--red);   box-shadow:0 0 5px var(--red); }
.lbl-on  { color:var(--green); }
.lbl-off { color:var(--red); }

/* ── Buttons ── */
.stButton > button {
    background: rgba(0,255,136,0.04) !important;
    color: var(--green) !important;
    border: 1px solid rgba(0,255,136,0.22) !important;
    border-radius: 9px !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.04em !important;
    transition: all 0.18s !important;
}
.stButton > button:hover {
    background: rgba(0,255,136,0.1) !important;
    border-color: var(--green) !important;
    box-shadow: 0 0 16px rgba(0,255,136,0.15) !important;
}
.stButton > button:active { transform:scale(0.97) !important; }

/* ── CHAT header ── */
.chat-hdr {
    display:flex; align-items:center; gap:0.75rem;
    padding:0.65rem 1.3rem;
    background:rgba(2,10,5,0.92);
    border-bottom:1px solid var(--glass-bdr);
    backdrop-filter:blur(20px);
    position:sticky; top:0; z-index:200;
    box-shadow:0 2px 16px rgba(0,0,0,0.4);
}
.hdr-icon { font-size:1.2rem; line-height:1; }
.hdr-title {
    font-family:var(--mono); font-size:0.95rem;
    color:var(--green); text-shadow:0 0 10px rgba(0,255,136,0.4); flex:1;
}
.hdr-status { display:flex; align-items:center; gap:5px; font-family:var(--mono); font-size:0.68rem; }

/* Messages */
.msgs { padding:1rem 1.3rem 0.5rem; }

/* ── Chat bubbles ── */
.row-user { display:flex; justify-content:flex-end; margin:0.4rem 0; }
.row-ai   { display:flex; justify-content:flex-start; margin:0.4rem 0; }

.bubble {
    max-width:70%; padding:0.6rem 0.95rem;
    border-radius:15px; font-size:0.93rem; line-height:1.65; word-break:break-word;
}
.bub-user {
    background:linear-gradient(135deg,rgba(0,255,136,0.13),rgba(0,170,80,0.07));
    border:1px solid rgba(0,255,136,0.22);
    color:var(--text); font-family:var(--sans);
    border-bottom-right-radius:4px;
}
.bub-ai {
    background:rgba(5,16,10,0.9);
    border:1px solid rgba(0,255,136,0.12);
    color:var(--text); font-family:var(--mono); font-size:0.87rem;
    border-bottom-left-radius:4px;
    box-shadow:0 2px 10px rgba(0,0,0,0.3);
}

/* File attach pill */
.attach-row { display:flex; justify-content:flex-end; margin-top:3px; }
.attach-pill {
    font-family:var(--mono); font-size:0.69rem; color:var(--text-dim);
    background:rgba(0,255,136,0.04); border:1px solid rgba(0,255,136,0.16);
    border-radius:999px; padding:2px 10px;
}

/* Thinking dots */
@keyframes pd { 0%,80%,100%{opacity:.2;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }
.thinking { display:inline-flex; gap:5px; align-items:center; padding:3px 0; }
.thinking span {
    width:7px; height:7px; border-radius:50%;
    background:var(--green); opacity:.2;
    animation: pd 1.2s infinite ease-in-out;
}
.thinking span:nth-child(2) { animation-delay:.2s; }
.thinking span:nth-child(3) { animation-delay:.4s; }

/* Cursor */
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
.cur {
    display:inline-block; width:2px; height:.9em;
    background:var(--green);
    animation:blink .85s step-end infinite;
    vertical-align:text-bottom; margin-left:2px; border-radius:1px;
}

/* File widget */
.file-wgt {
    display:flex; align-items:center; justify-content:space-between; gap:.7rem;
    padding:.5rem .85rem;
    background:rgba(0,255,136,0.04); border:1px solid rgba(0,255,136,0.2);
    border-radius:9px; font-family:var(--mono); font-size:0.78rem;
    color:var(--text-dim); margin-top:.45rem;
}
.file-wgt a {
    color:var(--green) !important; text-decoration:none !important;
    font-size:.78rem; white-space:nowrap;
    padding:2px 9px; border:1px solid rgba(0,255,136,0.28); border-radius:5px;
    transition:background .15s;
}
.file-wgt a:hover { background:rgba(0,255,136,0.1) !important; }

/* Generating spinner */
@keyframes spin { to{transform:rotate(360deg)} }
.gen-spin {
    display:inline-block; width:11px; height:11px;
    border:2px solid rgba(0,255,136,0.18); border-top-color:var(--green);
    border-radius:50%; animation:spin .75s linear infinite; flex-shrink:0;
}

/* ── Input area ── */
.input-area {
    position:sticky; bottom:0;
    background:rgba(2,10,5,0.95);
    border-top:1px solid var(--glass-bdr);
    backdrop-filter:blur(20px);
    padding:0.6rem 1.3rem 0.75rem;
    z-index:150;
}

/* Chat input */
[data-testid="stChatInputContainer"] { background:transparent !important; border:none !important; padding:0 !important; }
[data-testid="stChatInput"] {
    background:rgba(4,14,8,0.92) !important;
    border:1px solid var(--glass-bdr) !important;
    border-radius:11px !important;
    color:var(--text) !important; font-family:var(--mono) !important;
    transition:border-color .2s, box-shadow .2s;
}
[data-testid="stChatInput"]:focus-within {
    border-color:rgba(0,255,136,0.4) !important;
    box-shadow:0 0 18px rgba(0,255,136,0.1) !important;
}
[data-testid="stChatInput"] textarea { color:var(--text) !important; font-family:var(--mono) !important; font-size:.88rem !important; }
[data-testid="stChatInput"] button { color:var(--green) !important; }

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background:rgba(0,255,136,0.02) !important;
    border:1px dashed rgba(0,255,136,0.18) !important;
    border-radius:8px !important;
}
[data-testid="stFileUploaderDropzone"] * { color:var(--text-dim) !important; font-family:var(--mono) !important; font-size:.78rem !important; }
[data-testid="stFileUploadDeleteBtn"] button { color:var(--red) !important; }

/* Pending badge */
.pending {
    display:inline-flex; align-items:center; gap:5px;
    font-family:var(--mono); font-size:0.7rem;
    color:var(--green); background:rgba(0,255,136,0.05);
    border:1px solid rgba(0,255,136,0.2); border-radius:999px; padding:2px 10px 2px 7px;
    margin-top:5px;
}

/* Home footer */
.hm-footer { text-align:center; margin-top:2.5rem; font-family:var(--mono); font-size:0.65rem; color:var(--text-dim); letter-spacing:.15em; }
</style>
"""

# ── Session init ──────────────────────────────────────────────────────────────
def _init():
    for k, v in {
        "page": "home", "active_model": None,
        "messages": [], "pending_file": None,
        "model_status": {}, "show_upload": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
st.markdown(CSS, unsafe_allow_html=True)

# ── Nav ───────────────────────────────────────────────────────────────────────
def go_home():
    for k, v in {"page":"home","active_model":None,"messages":[],"pending_file":None,"show_upload":False}.items():
        st.session_state[k] = v

def go_chat(label):
    for k, v in {"page":"chat","active_model":label,"messages":[],"pending_file":None,"show_upload":False}.items():
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
#  HOME PAGE
# ─────────────────────────────────────────────────────────────────────────────
def render_home():
    st.markdown('<div class="home-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="home-logo">⚡ SPARTAN AI</div>
    <div class="home-byline">Built by Dallin Geurts &nbsp;·&nbsp; Powered by Ollama</div>
    <div class="home-desc">
        A suite of AI tools built for educators and students — generate assignments,
        grade with consistency, detect AI-written content, and give students a
        guided learning companion, all in one place.
    </div>
    <hr class="div">
    <div class="sec-label">▸ select a module to begin</div>
    """, unsafe_allow_html=True)

    cols = st.columns(2, gap="large")
    for i, label in enumerate(MODEL_MAP):
        mid = MODEL_MAP[label]
        if mid not in st.session_state.model_status:
            st.session_state.model_status[mid] = check_model_online(mid)
        online = st.session_state.model_status[mid]
        dc = "on" if online else "off"
        lc = "lbl-on" if online else "lbl-off"
        lt = "ONLINE" if online else "OFFLINE"

        with cols[i % 2]:
            st.markdown(f"""
            <div class="model-card">
                <div class="card-icon">{MODEL_ICONS[label]}</div>
                <div class="card-title">{label}</div>
                <div class="card-desc">{MODEL_DESC[label]}</div>
                <div class="card-status">
                    <span class="dot {dc}"></span>
                    <span class="{lc}">{lt}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            if st.button(f"Open {label}", key=f"open_{label}", use_container_width=True):
                go_chat(label); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, mid_col, _ = st.columns([3,2,3])
    with mid_col:
        if st.button("⟳  Refresh Status", use_container_width=True):
            st.session_state.model_status = {}; st.rerun()

    st.markdown('<div class="hm-footer">SPARTAN AI · v1.0 · dgeurts</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT — bubble renderers
# ─────────────────────────────────────────────────────────────────────────────
def _render_user_bubble(content: str, file_att):
    txt      = safe_html(content)
    file_htm = ""
    if file_att:
        file_htm = (
            f'<div class="attach-row">'
            f'<span class="attach-pill">📎 {html_lib.escape(file_att["name"])}</span>'
            f'</div>'
        )
    st.markdown(
        f'<div class="row-user"><div>'
        f'<div class="bubble bub-user">{txt}</div>'
        f'{file_htm}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _segments_to_html(segments: list) -> str:
    parts = []
    for seg in segments:
        if seg["type"] == "text":
            t = safe_html(seg["content"])
            if t:
                parts.append(f'<div style="margin-bottom:.35rem">{t}</div>')
        elif seg["type"] == "file":
            ft    = seg["filetype"]
            fname = html_lib.escape(seg["filename"])
            enc   = base64.b64encode(seg["content"].encode()).decode()
            parts.append(
                f'<div class="file-wgt">'
                f'<span>📄 {fname} <span style="opacity:.5">({ft.upper()})</span></span>'
                f'<a href="data:text/plain;base64,{enc}" download="{seg["filename"]}">⬇ Download</a>'
                f'</div>'
            )
    return "".join(parts)


def render_message(msg: dict):
    if msg["role"] == "user":
        _render_user_bubble(msg["content"], msg.get("file"))
    else:
        segs  = msg.get("segments", [])
        inner = _segments_to_html(segs) if segs else safe_html(msg.get("content",""))
        st.markdown(
            f'<div class="row-ai"><div class="bubble bub-ai">{inner}</div></div>',
            unsafe_allow_html=True,
        )


def _thinking_html():
    return (
        '<div class="row-ai"><div class="bubble bub-ai" style="padding:.6rem .95rem">'
        '<div class="thinking"><span></span><span></span><span></span></div>'
        '</div></div>'
    )


def _gen_file_html(ft: str, fname: str):
    return (
        '<div class="row-ai"><div class="bubble bub-ai">'
        f'<div class="file-wgt" style="opacity:.8">'
        f'<span class="gen-spin"></span>'
        f'<span>Generating {html_lib.escape(fname)}&nbsp;<span style="opacity:.5">({ft.upper()})…</span></span>'
        f'</div></div></div>'
    )


def _streaming_html(text: str):
    return (
        f'<div class="row-ai"><div class="bubble bub-ai">'
        f'{safe_html(text)}<span class="cur"></span>'
        f'</div></div>'
    )


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT PAGE
# ─────────────────────────────────────────────────────────────────────────────
def render_chat():
    label    = st.session_state.active_model
    model_id = MODEL_MAP[label]
    online   = st.session_state.model_status.get(model_id, False)
    dc = "on" if online else "off"
    lc = "lbl-on" if online else "lbl-off"
    lt = "ONLINE" if online else "OFFLINE"

    # ── Sticky header ──
    st.markdown(f"""
    <div class="chat-hdr">
        <span class="hdr-icon">{MODEL_ICONS[label]}</span>
        <span class="hdr-title">{label}</span>
        <div class="hdr-status">
            <span class="dot {dc}"></span>
            <span class="{lc}">{lt}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Home button ──
    tb_l, _ = st.columns([1, 9])
    with tb_l:
        if st.button("⟵ Home", key="btn_home"):
            go_home(); st.rerun()

    # ── Message history ──
    st.markdown('<div class="msgs">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        render_message(msg)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Input area ──
    st.markdown('<div class="input-area">', unsafe_allow_html=True)

    user_input = st.chat_input("Message Spartan AI…", key="chat_input")

    # Attach button + pending badge
    btn_col, badge_col = st.columns([1, 7])
    with btn_col:
        if st.button("📎 Attach", key="toggle_up"):
            st.session_state.show_upload = not st.session_state.show_upload
    with badge_col:
        if st.session_state.pending_file:
            st.markdown(
                f'<div style="padding-top:5px">'
                f'<span class="pending">📎 {html_lib.escape(st.session_state.pending_file["name"])}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if st.session_state.show_upload:
        upl = st.file_uploader(
            "Attach file — used in your next message only",
            key="file_uploader",
            label_visibility="collapsed",
        )
        if upl is not None:
            ext  = Path(upl.name).suffix.lower()
            raw  = upl.read()
            body = extract_text_from_image(raw) if ext in IMAGE_EXTENSIONS else raw.decode("utf-8", errors="replace")
            st.session_state.pending_file = {"name": upl.name, "ext": ext, "body": body}
            st.session_state.show_upload  = False
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Handle send ──
    if user_input:
        file_att     = st.session_state.pending_file
        full_content = build_user_content(user_input, file_att)

        st.session_state.messages.append({"role":"user","content":user_input,"file":file_att})
        st.session_state.pending_file = None
        st.session_state.show_upload  = False

        # Build Ollama history
        last_idx    = len(st.session_state.messages) - 1
        ollama_msgs = []
        for idx, m in enumerate(st.session_state.messages):
            if m["role"] == "user":
                c = full_content if idx == last_idx else build_user_content(m["content"], m.get("file"))
                ollama_msgs.append({"role":"user","content":c})
            else:
                ollama_msgs.append({"role":"assistant","content":m.get("content","")})

        # Render user bubble
        _render_user_bubble(user_input, file_att)

        think_ph  = st.empty()
        stream_ph = st.empty()

        think_ph.markdown(_thinking_html(), unsafe_allow_html=True)

        raw_response    = ""
        in_file_block   = False
        file_ft         = ""
        file_fn         = ""
        started         = False

        try:
            for token in stream_chat(model_id, ollama_msgs):
                raw_response += token

                if not started:
                    think_ph.empty()
                    started = True

                # Detect file block open
                if not in_file_block:
                    fm = re.search(r'\[output-file-([a-zA-Z0-9]+)-([^\]]+)\]', raw_response)
                    if fm:
                        file_ft = fm.group(1)
                        file_fn = fm.group(2)
                        closing = f'[/output-file-{file_ft}-{file_fn}]'
                        if closing not in raw_response:
                            in_file_block = True

                # Detect file block close
                if in_file_block:
                    closing = f'[/output-file-{file_ft}-{file_fn}]'
                    if closing in raw_response:
                        in_file_block = False

                if in_file_block:
                    stream_ph.markdown(_gen_file_html(file_ft, file_fn), unsafe_allow_html=True)
                else:
                    clean = _strip_tags(raw_response)
                    stream_ph.markdown(_streaming_html(clean), unsafe_allow_html=True)

        except Exception as e:
            think_ph.empty()
            raw_response = f"[Connection error: {e}]"

        think_ph.empty()
        stream_ph.empty()

        segs = parse_output(raw_response)
        st.session_state.messages.append({"role":"assistant","content":raw_response,"segments":segs})
        st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────
if st.session_state.page == "home":
    render_home()
else:
    render_chat()
