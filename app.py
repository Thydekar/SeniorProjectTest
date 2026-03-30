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
            names = [t.get("name","").split(":")[0] for t in r.json().get("models",[])]
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
    s = re.sub(r'\[/?output-text\]', '', s)
    s = re.sub(r'\[/?input-[^\]]+\]', '', s)
    s = re.sub(r'\[output-file-[^\]]+\]', '', s)
    s = re.sub(r'\[/output-file-[^\]]+\]', '', s)
    return s.strip()

def parse_output(raw: str) -> list:
    file_pat = re.compile(
        r'\[output-file-([a-zA-Z0-9]+)-([^\]]+)\](.*?)\[/output-file-\1-\2\]',
        re.DOTALL,
    )
    text_pat = re.compile(r'\[output-text\](.*?)\[/output-text\]', re.DOTALL)
    all_m = sorted(list(file_pat.finditer(raw)) + list(text_pat.finditer(raw)), key=lambda m: m.start())

    segments, last = [], 0
    for m in all_m:
        before = _strip_tags(raw[last:m.start()])
        if before:
            segments.append({"type":"text","content":before})
        if m.lastindex == 3:
            segments.append({"type":"file","filetype":m.group(1),"filename":m.group(2),"content":m.group(3).strip()})
        else:
            txt = _strip_tags(m.group(1))
            if txt:
                segments.append({"type":"text","content":txt})
        last = m.end()

    tail = _strip_tags(raw[last:])
    if tail:
        segments.append({"type":"text","content":tail})
    if not segments:
        segments.append({"type":"text","content":_strip_tags(raw) or raw})
    return segments

def safe_html(text: str) -> str:
    """Escape for HTML. Preserve intentional newlines but never add extras."""
    return html_lib.escape(str(text)).replace("\n", "<br>")

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

/* ── Variables ── */
:root {
    --green:      #00ff88;
    --green-dim:  #00cc6a;
    --green-glow: rgba(0,255,136,0.16);
    --red:        #ff4455;
    --glass-bg:   rgba(8,20,13,0.82);
    --glass-bdr:  rgba(0,255,136,0.13);
    --shine:      rgba(255,255,255,0.03);
    --bg:         #020a05;
    --text:       #c8ffe0;
    --text-dim:   #4a7560;
    --mono:       'Share Tech Mono', monospace;
    --sans:       'Rajdhani', sans-serif;
    --pad-x:      2.2rem;         /* consistent horizontal padding */
    --bar-h:      120px;          /* height reserved for bottom bar */
}

/* ── Reset / Base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}

/* Grid */
[data-testid="stAppViewContainer"]::before {
    content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
    background-image:
        linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px);
    background-size: 44px 44px;
}
/* Scanlines */
[data-testid="stAppViewContainer"]::after {
    content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
    background: repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 4px);
}

[data-testid="stMain"] { background:transparent !important; position:relative; z-index:1; }

/* Strip Streamlit chrome completely */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"],
[data-testid="stStatusWidget"] { display:none !important; }

/* Remove ALL Streamlit default padding — we control it ourselves */
.block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 0 !important;
    gap: 0 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(0,255,136,0.15); border-radius:2px; }
::-webkit-scrollbar-thumb:hover { background:rgba(0,255,136,0.3); }

/* ── Buttons ── */
.stButton > button {
    background: rgba(0,255,136,0.04) !important;
    color: var(--green) !important;
    border: 1px solid rgba(0,255,136,0.2) !important;
    border-radius: 9px !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.04em !important;
    padding: 0.45rem 0.9rem !important;
    transition: all 0.18s !important;
    white-space: nowrap !important;
}
.stButton > button:hover {
    background: rgba(0,255,136,0.1) !important;
    border-color: var(--green) !important;
    box-shadow: 0 0 14px rgba(0,255,136,0.14) !important;
}
.stButton > button:active { transform: scale(0.97) !important; }

/* ───────────────────────────────────────
   HOME PAGE
─────────────────────────────────────── */
.home-wrap {
    max-width: 900px;
    margin: 0 auto;
    padding: 3rem var(--pad-x) 3rem;
}
.home-logo {
    font-family: var(--mono);
    font-size: 2.8rem;
    color: var(--green);
    text-shadow: 0 0 22px var(--green), 0 0 55px rgba(0,255,136,0.22);
    letter-spacing: 0.1em;
    text-align: center;
}
.home-byline {
    font-family: var(--mono); font-size: 0.67rem;
    color: var(--text-dim); letter-spacing: 0.28em;
    text-transform: uppercase; text-align: center; margin-top:0.45rem;
}
.home-desc {
    font-family: var(--sans); font-size: 1rem;
    color: rgba(200,255,224,0.7); text-align:center;
    max-width:520px; margin:1.5rem auto 0; line-height:1.8;
}
.home-divider {
    border:none; border-top:1px solid var(--glass-bdr);
    margin:2rem 0 1.5rem;
}
.sec-label {
    font-family:var(--mono); font-size:0.65rem; color:var(--text-dim);
    letter-spacing:0.3em; text-transform:uppercase; text-align:center; margin-bottom:1.2rem;
}
.home-footer {
    text-align:center; margin-top:2.5rem;
    font-family:var(--mono); font-size:0.63rem;
    color:var(--text-dim); letter-spacing:.15em;
}

/* Model cards */
.model-card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-bdr);
    backdrop-filter: blur(18px); -webkit-backdrop-filter:blur(18px);
    border-radius: 13px;
    padding: 1.1rem 1rem 0.9rem;
    position: relative; overflow:hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.45), 0 0 0 1px var(--shine) inset;
    margin-bottom: 0.3rem;
}
.model-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:1px;
    background:linear-gradient(90deg,transparent,var(--green),transparent); opacity:0.3;
}
.card-icon  { font-size:1.5rem; line-height:1; margin-bottom:0.35rem; }
.card-title { font-family:var(--sans); font-weight:700; font-size:0.98rem; color:var(--green); letter-spacing:0.04em; margin-bottom:0.2rem; }
.card-desc  { font-family:var(--sans); font-size:0.82rem; color:var(--text-dim); line-height:1.5; }
.card-status { display:flex; align-items:center; gap:5px; margin-top:0.75rem; font-family:var(--mono); font-size:0.68rem; }
.dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.dot.on  { background:var(--green); box-shadow:0 0 5px var(--green); }
.dot.off { background:var(--red);   box-shadow:0 0 5px var(--red); }
.lbl-on  { color:var(--green); }
.lbl-off { color:var(--red); }

/* ───────────────────────────────────────
   CHAT PAGE — overall structure
─────────────────────────────────────── */
/* Sticky top header */
.chat-hdr {
    display:flex; align-items:center; gap:0.7rem;
    padding: 0.6rem var(--pad-x);
    background: rgba(2,10,5,0.96);
    border-bottom: 1px solid var(--glass-bdr);
    backdrop-filter: blur(20px); -webkit-backdrop-filter:blur(20px);
    position: sticky; top:0; z-index:300;
    box-shadow: 0 1px 0 rgba(0,255,136,0.06), 0 3px 14px rgba(0,0,0,0.35);
}
.hdr-icon  { font-size:1.15rem; line-height:1; }
.hdr-title { font-family:var(--mono); font-size:0.92rem; color:var(--green); text-shadow:0 0 9px rgba(0,255,136,0.4); flex:1; }
.hdr-status { display:flex; align-items:center; gap:5px; font-family:var(--mono); font-size:0.67rem; }

/* Message list — padded symmetrically, leaves room for fixed bar */
.msgs-wrap {
    padding: 1rem var(--pad-x) calc(var(--bar-h) + 1rem);
}

/* ── Bubble rows ── */
.row-user { display:flex; justify-content:flex-end;  margin:0.35rem 0; }
.row-ai   { display:flex; justify-content:flex-start; margin:0.35rem 0; }

/* Bubbles — max-width so they never span full width */
.bubble {
    max-width: min(68%, 680px);
    padding: 0.55rem 0.9rem;
    border-radius: 14px;
    font-size: 0.92rem;
    line-height: 1.6;
    word-break: break-word;
    /* ← key: don't force a minimum width */
    display: inline-block;
}
.bub-user {
    background: linear-gradient(135deg,rgba(0,255,136,0.12),rgba(0,160,75,0.07));
    border: 1px solid rgba(0,255,136,0.2);
    color: var(--text); font-family: var(--sans);
    border-bottom-right-radius: 4px;
}
.bub-ai {
    background: rgba(5,15,10,0.92);
    border: 1px solid rgba(0,255,136,0.11);
    color: var(--text); font-family: var(--mono); font-size: 0.86rem;
    border-bottom-left-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.28);
}

/* File attachment pill under user bubble */
.attach-row  { display:flex; justify-content:flex-end; margin-top:3px; }
.attach-pill {
    font-family:var(--mono); font-size:0.68rem; color:var(--text-dim);
    background:rgba(0,255,136,0.04); border:1px solid rgba(0,255,136,0.14);
    border-radius:999px; padding:1px 9px;
}

/* Thinking dots */
@keyframes pd { 0%,80%,100%{opacity:.18;transform:scale(.78)} 40%{opacity:1;transform:scale(1)} }
.thinking       { display:inline-flex; gap:5px; align-items:center; }
.thinking span  {
    width:7px; height:7px; border-radius:50%;
    background:var(--green); opacity:.18;
    animation:pd 1.2s infinite ease-in-out;
}
.thinking span:nth-child(2) { animation-delay:.2s; }
.thinking span:nth-child(3) { animation-delay:.4s; }

/* Typing cursor */
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
.cur {
    display:inline-block; width:2px; height:.88em;
    background:var(--green);
    animation:blink .85s step-end infinite;
    vertical-align:text-bottom; margin-left:2px; border-radius:1px;
}

/* File download widget */
.file-wgt {
    display:flex; align-items:center; justify-content:space-between; gap:.65rem;
    padding:.45rem .8rem;
    background:rgba(0,255,136,0.04); border:1px solid rgba(0,255,136,0.18);
    border-radius:8px; font-family:var(--mono); font-size:0.76rem;
    color:var(--text-dim); margin-top:.4rem;
}
.file-wgt a {
    color:var(--green) !important; text-decoration:none !important;
    font-size:.76rem; white-space:nowrap;
    padding:2px 8px; border:1px solid rgba(0,255,136,0.26); border-radius:5px;
    transition:background .15s;
}
.file-wgt a:hover { background:rgba(0,255,136,0.1) !important; }

/* Generating spinner */
@keyframes spin { to{transform:rotate(360deg)} }
.gen-spin {
    display:inline-block; width:10px; height:10px;
    border:2px solid rgba(0,255,136,0.15); border-top-color:var(--green);
    border-radius:50%; animation:spin .75s linear infinite; flex-shrink:0;
}

/* ───────────────────────────────────────
   FIXED BOTTOM BAR
   — this is pure HTML rendered at page bottom,
     not a Streamlit widget layer, so no black bar conflict
─────────────────────────────────────── */
.bottom-bar {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    z-index: 400;                          /* above everything */
    background: rgba(2,10,5,0.97);
    border-top: 1px solid var(--glass-bdr);
    backdrop-filter: blur(24px); -webkit-backdrop-filter:blur(24px);
    padding: 0.6rem var(--pad-x) 0.7rem;
}

/* Row 1 — icon buttons + chat input + send */
.bar-row1 {
    display: flex;
    align-items: center;
    gap: 0.55rem;
}

/* Pending file badge inside bar */
.bar-badge {
    display:inline-flex; align-items:center; gap:4px;
    font-family:var(--mono); font-size:0.67rem; color:var(--green);
    background:rgba(0,255,136,0.05); border:1px solid rgba(0,255,136,0.18);
    border-radius:999px; padding:2px 8px 2px 6px; white-space:nowrap;
}

/* Row 2 — collapsible uploader */
.bar-row2 { margin-top: 0.45rem; }

/* ── Streamlit chat input lives inside the bar via st.container ── */
/* We override its wrapper so it fills the flex row */
[data-testid="stChatInputContainer"] {
    flex: 1 !important;
    background: transparent !important;
    padding: 0 !important;
    border: none !important;
    min-width: 0 !important;
}
[data-testid="stChatInput"] {
    background: rgba(3,12,7,0.95) !important;
    border: 1px solid var(--glass-bdr) !important;
    border-radius: 10px !important;
    color: var(--text) !important; font-family: var(--mono) !important;
    transition: border-color .2s, box-shadow .2s;
    width: 100% !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: rgba(0,255,136,0.38) !important;
    box-shadow: 0 0 16px rgba(0,255,136,0.09) !important;
}
[data-testid="stChatInput"] textarea {
    color: var(--text) !important; font-family: var(--mono) !important; font-size:.87rem !important;
}
[data-testid="stChatInput"] button { color: var(--green) !important; }

/* File uploader strip */
[data-testid="stFileUploaderDropzone"] {
    background: rgba(0,255,136,0.02) !important;
    border: 1px dashed rgba(0,255,136,0.16) !important;
    border-radius:7px !important; padding: 0.4rem 0.7rem !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color:var(--text-dim) !important; font-family:var(--mono) !important; font-size:.75rem !important;
}
[data-testid="stFileUploadDeleteBtn"] button { color:var(--red) !important; }

/* Hide the file uploader label */
[data-testid="stFileUploaderDropzoneInstructions"] div:first-child { display:none; }
</style>
"""

# ── Session init ──────────────────────────────────────────────────────────────
def _init():
    for k, v in {
        "page":"home", "active_model":None,
        "messages":[], "pending_file":None,
        "model_status":{}, "show_upload":False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
st.markdown(CSS, unsafe_allow_html=True)

# ── Nav ───────────────────────────────────────────────────────────────────────
def go_home():
    for k,v in {"page":"home","active_model":None,"messages":[],"pending_file":None,"show_upload":False}.items():
        st.session_state[k]=v

def go_chat(label):
    for k,v in {"page":"chat","active_model":label,"messages":[],"pending_file":None,"show_upload":False}.items():
        st.session_state[k]=v

def new_chat():
    st.session_state.messages    = []
    st.session_state.pending_file = None
    st.session_state.show_upload  = False


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
    <hr class="home-divider">
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

    st.markdown('<div class="home-footer">SPARTAN AI · v1.0 · dgeurts</div></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT — renderers
# ─────────────────────────────────────────────────────────────────────────────
def _segments_to_html(segments: list) -> str:
    parts = []
    for seg in segments:
        if seg["type"] == "text":
            t = safe_html(seg["content"])
            if t:
                parts.append(f'<div style="margin-bottom:.3rem">{t}</div>')
        elif seg["type"] == "file":
            ft    = seg["filetype"]
            fname = html_lib.escape(seg["filename"])
            enc   = base64.b64encode(seg["content"].encode()).decode()
            parts.append(
                f'<div class="file-wgt">'
                f'<span>📄 {fname} <span style="opacity:.45">({ft.upper()})</span></span>'
                f'<a href="data:text/plain;base64,{enc}" download="{seg["filename"]}">⬇ Download</a>'
                f'</div>'
            )
    return "".join(parts)

def render_message(msg: dict):
    if msg["role"] == "user":
        txt = safe_html(msg["content"])
        fat = msg.get("file")
        pill = (
            f'<div class="attach-row">'
            f'<span class="attach-pill">📎 {html_lib.escape(fat["name"])}</span>'
            f'</div>'
        ) if fat else ""
        st.markdown(
            f'<div class="row-user"><div>'
            f'<div class="bubble bub-user">{txt}</div>'
            f'{pill}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        segs  = msg.get("segments", [])
        inner = _segments_to_html(segs) if segs else safe_html(msg.get("content",""))
        st.markdown(
            f'<div class="row-ai"><div class="bubble bub-ai">{inner}</div></div>',
            unsafe_allow_html=True,
        )

def _thinking_html():
    return ('<div class="row-ai"><div class="bubble bub-ai">'
            '<div class="thinking"><span></span><span></span><span></span></div>'
            '</div></div>')

def _gen_file_html(ft, fname):
    return (f'<div class="row-ai"><div class="bubble bub-ai">'
            f'<div class="file-wgt" style="opacity:.75">'
            f'<span class="gen-spin"></span>'
            f'<span>Generating {html_lib.escape(fname)} <span style="opacity:.45">({ft.upper()})…</span></span>'
            f'</div></div></div>')

def _streaming_html(text: str):
    return (f'<div class="row-ai"><div class="bubble bub-ai">'
            f'{safe_html(text)}<span class="cur"></span>'
            f'</div></div>')


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

    # ── Sticky top header ──
    st.markdown(f"""
    <div class="chat-hdr">
        <span class="hdr-icon">{MODEL_ICONS[label]}</span>
        <span class="hdr-title">{label}</span>
        <div class="hdr-status">
            <span class="dot {dc}"></span>
            <span class="{lc}">{lt}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Message history ──
    st.markdown('<div class="msgs-wrap">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        render_message(msg)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── FIXED BOTTOM BAR ──
    # We render the bar as an HTML shell, then use Streamlit widgets inside it.
    # The trick: render a placeholder container that Streamlit appends into,
    # then use CSS position:fixed on the outer shell.
    # Because Streamlit always appends to the end of the page body,
    # the chat_input + buttons will naturally appear last (inside the fixed bar area).

    # Pending file badge HTML (injected into bar row 1)
    badge_html = ""
    if st.session_state.pending_file:
        fname = html_lib.escape(st.session_state.pending_file["name"])
        badge_html = f'<span class="bar-badge">📎 {fname}</span>'

    # Inject the fixed bar shell with badge
    st.markdown(f"""
    <div class="bottom-bar" id="spartan-bar">
        <div class="bar-row1" id="bar-row1-anchor">
            <!-- Streamlit widgets below will be placed by the browser after this shell -->
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Now render actual Streamlit widgets — they appear after the shell in DOM,
    # but the fixed bar CSS makes the visual layer correct.
    # We use a custom container div to group them.

    # Row of buttons + chat input + badge
    # Streamlit columns let us lay them out side by side
    c_home, c_new, c_attach, c_input, c_badge = st.columns([1.1, 1.1, 1.1, 8, 2.2])

    with c_home:
        if st.button("⟵ Home", key="btn_home"):
            go_home(); st.rerun()

    with c_new:
        if st.button("✦ New", key="btn_new"):
            new_chat(); st.rerun()

    with c_attach:
        label_attach = "📎 ▴" if st.session_state.show_upload else "📎 Attach"
        if st.button(label_attach, key="btn_attach"):
            st.session_state.show_upload = not st.session_state.show_upload
            st.rerun()

    with c_input:
        user_input = st.chat_input("Message Spartan AI…", key="chat_input")

    with c_badge:
        if st.session_state.pending_file:
            fname = html_lib.escape(st.session_state.pending_file["name"])
            st.markdown(
                f'<div style="display:flex;align-items:center;height:100%;padding-top:4px">'
                f'<span class="bar-badge">📎 {fname}</span></div>',
                unsafe_allow_html=True,
            )

    # File uploader (collapsible row below input)
    if st.session_state.show_upload:
        upl = st.file_uploader(
            "Attach — used in next message only",
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

    # ── Handle send ──
    if user_input:
        file_att     = st.session_state.pending_file
        full_content = build_user_content(user_input, file_att)

        st.session_state.messages.append({"role":"user","content":user_input,"file":file_att})
        st.session_state.pending_file = None
        st.session_state.show_upload  = False

        last_idx    = len(st.session_state.messages) - 1
        ollama_msgs = []
        for idx, m in enumerate(st.session_state.messages):
            if m["role"] == "user":
                c_ = full_content if idx == last_idx else build_user_content(m["content"], m.get("file"))
                ollama_msgs.append({"role":"user","content":c_})
            else:
                ollama_msgs.append({"role":"assistant","content":m.get("content","")})

        # Render user bubble immediately, then stream
        render_message(st.session_state.messages[-1])
        think_ph  = st.empty()
        stream_ph = st.empty()
        think_ph.markdown(_thinking_html(), unsafe_allow_html=True)

        raw_response  = ""
        in_file_block = False
        file_ft = file_fn = ""
        started = False

        try:
            for token in stream_chat(model_id, ollama_msgs):
                raw_response += token
                if not started:
                    think_ph.empty()
                    started = True

                if not in_file_block:
                    fm = re.search(r'\[output-file-([a-zA-Z0-9]+)-([^\]]+)\]', raw_response)
                    if fm:
                        file_ft = fm.group(1); file_fn = fm.group(2)
                        if f'[/output-file-{file_ft}-{file_fn}]' not in raw_response:
                            in_file_block = True
                if in_file_block:
                    if f'[/output-file-{file_ft}-{file_fn}]' in raw_response:
                        in_file_block = False

                if in_file_block:
                    stream_ph.markdown(_gen_file_html(file_ft, file_fn), unsafe_allow_html=True)
                else:
                    stream_ph.markdown(_streaming_html(_strip_tags(raw_response)), unsafe_allow_html=True)

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
