import streamlit as st
import requests
import json
import base64
import tempfile
import os
import re
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
NGROK_URL      = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
OLLAMA_TAGS_URL = f"{NGROK_URL}/api/tags"
USERNAME       = "dgeurts"
PASSWORD       = "thaidakar21"
OCR_CONFIG     = r"--oem 3 --psm 6"

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
    ".txt", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css",
    ".py", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rb", ".php",
    ".json", ".xml", ".yaml", ".yml", ".md", ".csv", ".sql", ".sh",
    ".bash", ".r", ".swift", ".kt", ".rs", ".dart", ".vue", ".svelte",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp"}

AUTH = (USERNAME, PASSWORD)

# ── Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spartan AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def check_model_online(model_name: str) -> bool:
    try:
        r = requests.get(OLLAMA_TAGS_URL, auth=AUTH, timeout=5)
        if r.status_code == 200:
            tags = r.json().get("models", [])
            names = [t.get("name", "").split(":")[0] for t in tags]
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


def build_user_content(text: str, file_info: dict | None) -> str:
    """Wrap user text (and optional file content) in the protocol tags."""
    parts = []
    if file_info:
        ext  = file_info["ext"]
        body = file_info["body"]
        if ext in IMAGE_EXTENSIONS:
            parts.append(f"[input-file-image-text]\n{body}\n[/input-file-image-text]")
        else:
            ft = ext.lstrip(".")
            parts.append(f"[input-file-{ft}-text]\n{body}\n[/input-file-{ft}-text]")
    parts.append(f"[input-user-text]\n{text}\n[/input-user-text]")
    return "\n".join(parts)


def stream_chat(model_name: str, messages: list):
    """Yield token strings from the Ollama streaming chat endpoint."""
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


def parse_output(raw: str):
    """
    Split raw AI output into a list of segments:
      {"type": "text",  "content": "..."}
      {"type": "file",  "filetype": "md", "filename": "out.md", "content": "..."}
    """
    segments = []
    pattern = re.compile(
        r'\[output-file-([a-zA-Z0-9]+)-([^\]]+)\](.*?)\[/output-file-\1-\2\]',
        re.DOTALL
    )
    text_pattern = re.compile(
        r'\[output-text\](.*?)\[/output-text\]',
        re.DOTALL
    )

    last = 0
    combined = list(pattern.finditer(raw)) + list(text_pattern.finditer(raw))
    combined.sort(key=lambda m: m.start())

    for m in combined:
        before = raw[last:m.start()].strip()
        if before:
            # strip any leftover tags
            clean = re.sub(r'\[/?output-text\]', '', before).strip()
            if clean:
                segments.append({"type": "text", "content": clean})
        if m.lastindex == 3:  # file match
            segments.append({
                "type": "file",
                "filetype": m.group(1),
                "filename": m.group(2),
                "content": m.group(3).strip(),
            })
        else:  # text match
            segments.append({"type": "text", "content": m.group(1).strip()})
        last = m.end()

    tail = raw[last:].strip()
    if tail:
        clean = re.sub(r'\[/?output-text\]', '', tail).strip()
        if clean:
            segments.append({"type": "text", "content": clean})

    if not segments:
        segments.append({"type": "text", "content": raw})

    return segments


# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

/* ── Root & Reset ── */
:root {
    --green:        #00ff88;
    --green-dim:    #00cc6a;
    --green-glow:   rgba(0,255,136,0.18);
    --green-glass:  rgba(0,255,136,0.07);
    --red:          #ff4466;
    --red-glow:     rgba(255,68,102,0.25);
    --glass-bg:     rgba(10,20,15,0.72);
    --glass-border: rgba(0,255,136,0.18);
    --glass-shine:  rgba(255,255,255,0.04);
    --bg:           #020a05;
    --text:         #c8ffe0;
    --text-dim:     #5a8a6a;
    --mono:         'Share Tech Mono', monospace;
    --sans:         'Rajdhani', sans-serif;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}

/* Grid background */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background-image:
        linear-gradient(rgba(0,255,136,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
}

/* Scanline overlay */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.06) 2px,
        rgba(0,0,0,0.06) 4px
    );
    pointer-events: none;
}

[data-testid="stMain"] {
    background: transparent !important;
    position: relative; z-index: 1;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Glass card ── */
.glass {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(20px) saturate(1.4);
    -webkit-backdrop-filter: blur(20px) saturate(1.4);
    box-shadow:
        0 0 0 1px var(--glass-shine) inset,
        0 8px 40px rgba(0,0,0,0.6),
        0 0 60px var(--green-glow);
    border-radius: 16px;
}

/* ── Home screen ── */
.home-hero {
    text-align: center;
    padding: 3rem 1rem 2rem;
}
.home-logo {
    font-family: var(--mono);
    font-size: 3.6rem;
    color: var(--green);
    text-shadow: 0 0 30px var(--green), 0 0 80px var(--green-glow);
    letter-spacing: 0.12em;
    line-height: 1;
}
.home-sub {
    font-family: var(--sans);
    font-size: 1.15rem;
    color: var(--text-dim);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 0.4rem;
}
.home-desc {
    font-family: var(--sans);
    font-size: 1.05rem;
    color: var(--text);
    max-width: 620px;
    margin: 1.8rem auto 0;
    line-height: 1.7;
    opacity: 0.85;
}
.divider {
    border: none;
    border-top: 1px solid var(--glass-border);
    margin: 2rem 0;
    box-shadow: 0 0 10px var(--green-glow);
}

/* ── Model cards ── */
.model-card {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    backdrop-filter: blur(16px);
    border-radius: 14px;
    padding: 1.4rem 1.2rem;
    cursor: pointer;
    transition: all 0.25s ease;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 0 0 1px var(--glass-shine) inset;
    position: relative;
    overflow: hidden;
}
.model-card::before {
    content:'';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--green), transparent);
    opacity: 0.5;
}
.model-card:hover {
    border-color: var(--green-dim);
    box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 0 30px var(--green-glow);
    transform: translateY(-3px);
}
.model-card-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.model-card-title {
    font-family: var(--sans);
    font-weight: 700;
    font-size: 1.1rem;
    color: var(--green);
    letter-spacing: 0.05em;
}
.model-card-desc {
    font-family: var(--sans);
    font-size: 0.88rem;
    color: var(--text-dim);
    margin-top: 0.4rem;
    line-height: 1.5;
}
.status-dot {
    display: inline-block;
    width: 9px; height: 9px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}
.status-online  { background: var(--green); box-shadow: 0 0 8px var(--green); }
.status-offline { background: var(--red);   box-shadow: 0 0 8px var(--red); }

/* ── Chat page ── */
.chat-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 1.5rem;
    background: var(--glass-bg);
    border-bottom: 1px solid var(--glass-border);
    backdrop-filter: blur(20px);
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 0 30px var(--green-glow);
}
.chat-header-title {
    font-family: var(--mono);
    font-size: 1.2rem;
    color: var(--green);
    text-shadow: 0 0 10px var(--green);
}

/* ── Bubbles ── */
.bubble-row-user  { display:flex; justify-content:flex-end;  margin:0.5rem 0; }
.bubble-row-ai    { display:flex; justify-content:flex-start; margin:0.5rem 0; }

.bubble {
    max-width: 68%;
    padding: 0.75rem 1.1rem;
    border-radius: 16px;
    font-family: var(--sans);
    font-size: 0.97rem;
    line-height: 1.6;
    position: relative;
    word-break: break-word;
}
.bubble-user {
    background: linear-gradient(135deg, rgba(0,255,136,0.18), rgba(0,200,100,0.10));
    border: 1px solid rgba(0,255,136,0.3);
    color: var(--text);
    border-bottom-right-radius: 4px;
    box-shadow: 0 0 20px rgba(0,255,136,0.08);
}
.bubble-ai {
    background: rgba(10,25,18,0.85);
    border: 1px solid var(--glass-border);
    color: var(--text);
    border-bottom-left-radius: 4px;
    font-family: var(--mono);
    font-size: 0.91rem;
    box-shadow: 0 0 20px rgba(0,0,0,0.4);
}
.bubble-file-attach {
    max-width: 68%;
    margin-top: 4px;
    padding: 0.35rem 0.8rem;
    border-radius: 10px;
    background: rgba(0,255,136,0.06);
    border: 1px solid rgba(0,255,136,0.2);
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--text-dim);
    display: inline-block;
}

/* Typing cursor */
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
.cursor {
    display: inline-block;
    width: 2px; height: 1em;
    background: var(--green);
    animation: blink 0.9s step-end infinite;
    vertical-align: text-bottom;
    margin-left: 2px;
}

/* File widget */
.file-widget {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.6rem 1rem;
    background: rgba(0,255,136,0.05);
    border: 1px solid rgba(0,255,136,0.25);
    border-radius: 10px;
    font-family: var(--mono);
    font-size: 0.85rem;
    color: var(--green);
    margin-top: 0.5rem;
    cursor: pointer;
    transition: background 0.2s;
}
.file-widget:hover { background: rgba(0,255,136,0.12); }

/* Generating spinner */
@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid rgba(0,255,136,0.25);
    border-top-color: var(--green);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
}

/* ── Streamlit overrides ── */
.stButton > button {
    background: var(--glass-bg) !important;
    color: var(--green) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    font-family: var(--mono) !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
    box-shadow: 0 0 12px var(--green-glow) !important;
}
.stButton > button:hover {
    background: var(--green-glass) !important;
    box-shadow: 0 0 24px var(--green-glow) !important;
}

.stTextInput > div > div > input,
.stTextArea textarea,
.stChatInput textarea {
    background: rgba(5,15,10,0.85) !important;
    border: 1px solid var(--glass-border) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    border-radius: 12px !important;
    box-shadow: 0 0 16px var(--green-glow) !important;
}
.stTextInput > div > div > input:focus,
.stChatInput textarea:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 30px var(--green-glow) !important;
}

/* Chat input bar wrapper — pin to bottom */
[data-testid="stChatInput"] {
    background: rgba(2,10,5,0.92) !important;
    border-top: 1px solid var(--glass-border) !important;
    backdrop-filter: blur(20px) !important;
    padding: 0.8rem 1rem !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: var(--glass-bg) !important;
    border: 1px dashed var(--glass-border) !important;
    border-radius: 12px !important;
    color: var(--text-dim) !important;
}

/* Select box */
[data-testid="stSelectbox"] > div > div {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    border-radius: 10px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,255,136,0.2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,255,136,0.4); }

/* Section headers */
.section-label {
    font-family: var(--mono);
    font-size: 0.72rem;
    color: var(--text-dim);
    letter-spacing: 0.25em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
}

/* Glowing tag badge */
.tag-badge {
    display: inline-block;
    padding: 2px 10px;
    border: 1px solid var(--green);
    border-radius: 999px;
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--green);
    text-shadow: 0 0 6px var(--green);
    box-shadow: 0 0 10px var(--green-glow);
    margin: 2px 3px;
}

.chat-messages-area {
    padding: 1rem 1rem 6rem;
    min-height: 60vh;
}
</style>
"""

# ── Session state init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "page":          "home",
        "active_model":  None,
        "messages":      [],   # {"role": "user"|"assistant", "content": str, "file": dict|None, "segments": list}
        "pending_file":  None, # {"name": str, "ext": str, "body": str}
        "model_status":  {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Inject CSS ───────────────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

# ── Navigation helpers ────────────────────────────────────────────────────────
def go_home():
    st.session_state.page         = "home"
    st.session_state.active_model = None
    st.session_state.messages     = []
    st.session_state.pending_file = None

def go_chat(model_label: str):
    st.session_state.page         = "chat"
    st.session_state.active_model = model_label
    st.session_state.messages     = []
    st.session_state.pending_file = None


# ─────────────────────────────────────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────────────────────────────────────
def render_home():
    st.markdown("""
    <div class="home-hero">
        <div class="home-logo">⚡ SPARTAN AI</div>
        <div class="home-sub">Built by Dallin Geurts &nbsp;·&nbsp; Powered by Ollama</div>
        <div class="home-desc">
            An intelligent suite of AI tools designed for educators and students.
            Generate assignments, grade with consistency, detect AI-written content,
            and give students a guided learning companion — all in one terminal.
        </div>
    </div>
    <hr class="divider">
    <div class="section-label" style="text-align:center;margin-bottom:1.5rem;">
        ▸ Select a module to begin
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2, gap="large")
    labels = list(MODEL_MAP.keys())

    for i, label in enumerate(labels):
        model_id = MODEL_MAP[label]
        col = cols[i % 2]

        # Check online status (cached per session)
        if model_id not in st.session_state.model_status:
            st.session_state.model_status[model_id] = check_model_online(model_id)
        online = st.session_state.model_status[model_id]

        status_cls  = "status-online"  if online else "status-offline"
        status_text = "ONLINE"         if online else "OFFLINE"
        status_icon = "●"

        with col:
            st.markdown(f"""
            <div class="model-card">
                <div class="model-card-icon">{MODEL_ICONS[label]}</div>
                <div class="model-card-title">{label}</div>
                <div class="model-card-desc">{MODEL_DESC[label]}</div>
                <div style="margin-top:0.9rem">
                    <span class="status-dot {status_cls}"></span>
                    <span style="font-family:var(--mono);font-size:0.75rem;color:{'var(--green)' if online else 'var(--red)'}">
                        {status_icon} {status_text}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Open {label}", key=f"open_{label}", use_container_width=True):
                go_chat(label)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Refresh status button
    _, mid, _ = st.columns([3, 2, 3])
    with mid:
        if st.button("⟳  Refresh Model Status", use_container_width=True):
            st.session_state.model_status = {}
            st.rerun()

    st.markdown("""
    <div style="text-align:center;margin-top:3rem;font-family:var(--mono);font-size:0.72rem;color:var(--text-dim);">
        SPARTAN AI &nbsp;·&nbsp; v1.0 &nbsp;·&nbsp; dgeurts
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CHAT PAGE
# ─────────────────────────────────────────────────────────────────────────────
def render_message(msg: dict):
    role     = msg["role"]
    content  = msg["content"]
    file_att = msg.get("file")
    segments = msg.get("segments", [])

    if role == "user":
        st.markdown(f"""
        <div class="bubble-row-user">
            <div>
                <div class="bubble bubble-user">{content}</div>
                {"" if not file_att else
                 f'<div style="display:flex;justify-content:flex-end;margin-top:4px;">'
                 f'<span class="bubble-file-attach">📎 {file_att["name"]}</span>'
                 f'</div>'}
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:  # assistant
        if segments:
            parts_html = []
            for seg in segments:
                if seg["type"] == "text":
                    txt = seg["content"].replace("\n", "<br>")
                    parts_html.append(f'<div style="margin-bottom:0.5rem">{txt}</div>')
                elif seg["type"] == "file":
                    encoded = base64.b64encode(seg["content"].encode()).decode()
                    mime    = "text/plain"
                    parts_html.append(
                        f'<div class="file-widget">'
                        f'<span>📄 {seg["filename"]} ({seg["filetype"].upper()})</span>'
                        f'<a href="data:{mime};base64,{encoded}" download="{seg["filename"]}" '
                        f'style="color:var(--green);text-decoration:none;margin-left:auto">⬇ Download</a>'
                        f'</div>'
                    )
            inner = "".join(parts_html)
        else:
            inner = content.replace("\n", "<br>")

        st.markdown(f"""
        <div class="bubble-row-ai">
            <div class="bubble bubble-ai">{inner}</div>
        </div>
        """, unsafe_allow_html=True)


def render_chat():
    label    = st.session_state.active_model
    model_id = MODEL_MAP[label]

    # ── Header ──
    online = st.session_state.model_status.get(model_id, False)
    dot    = f'<span class="status-dot {"status-online" if online else "status-offline"}"></span>'
    st.markdown(f"""
    <div class="chat-header">
        {MODEL_ICONS[label]}
        <span class="chat-header-title">{label}</span>
        <span style="font-family:var(--mono);font-size:0.75rem;color:{'var(--green)' if online else 'var(--red)'}">
            {dot} {"ONLINE" if online else "OFFLINE"}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Top toolbar: back + upload ──
    toolbar_left, toolbar_right = st.columns([1, 9])
    with toolbar_left:
        if st.button("⟵ Home", key="btn_home"):
            go_home()
            st.rerun()

    # File upload (popover pattern via expander)
    with toolbar_right:
        uploaded = st.file_uploader(
            "📎 Attach file (optional — used in your next message only)",
            key="file_uploader",
            label_visibility="collapsed",
        )
        if uploaded is not None:
            ext = Path(uploaded.name).suffix.lower()
            raw = uploaded.read()
            if ext in IMAGE_EXTENSIONS:
                body = extract_text_from_image(raw)
            elif ext in TEXT_EXTENSIONS or ext == "":
                body = raw.decode("utf-8", errors="replace")
            else:
                body = raw.decode("utf-8", errors="replace")
            st.session_state.pending_file = {"name": uploaded.name, "ext": ext, "body": body}
            st.success(f"📎 **{uploaded.name}** ready — will attach to your next message.")

    if st.session_state.pending_file:
        st.markdown(
            f'<span class="tag-badge">📎 {st.session_state.pending_file["name"]}</span>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="chat-messages-area">', unsafe_allow_html=True)

    # ── Render history ──
    for msg in st.session_state.messages:
        render_message(msg)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Chat input ──
    user_input = st.chat_input("Message Spartan AI…", key="chat_input")

    if user_input:
        file_att = st.session_state.pending_file
        full_content = build_user_content(user_input, file_att)

        # Save user message
        st.session_state.messages.append({
            "role":    "user",
            "content": user_input,
            "file":    file_att,
        })
        st.session_state.pending_file = None

        # Build messages for Ollama
        ollama_msgs = []
        for m in st.session_state.messages:
            if m["role"] == "user":
                idx = st.session_state.messages.index(m)
                if idx == len(st.session_state.messages) - 1:
                    ollama_msgs.append({"role": "user", "content": full_content})
                else:
                    plain = build_user_content(m["content"], m.get("file"))
                    ollama_msgs.append({"role": "user", "content": plain})
            else:
                ollama_msgs.append({"role": "assistant", "content": m["content"]})

        # Show user bubble immediately
        render_message(st.session_state.messages[-1])

        # Stream AI response
        with st.empty():
            raw_response = ""
            st.markdown(
                '<div class="bubble-row-ai"><div class="bubble bubble-ai">'
                '<span class="spinner"></span>thinking…'
                '</div></div>',
                unsafe_allow_html=True,
            )
            try:
                buf = ""
                display_placeholder = st.empty()
                for token in stream_chat(model_id, ollama_msgs):
                    raw_response += token
                    buf          += token
                    display_text  = raw_response.replace("\n", "<br>")
                    display_placeholder.markdown(
                        f'<div class="bubble-row-ai">'
                        f'<div class="bubble bubble-ai">{display_text}'
                        f'<span class="cursor"></span>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                raw_response = f"[Error contacting model: {e}]"

        segments = parse_output(raw_response)
        st.session_state.messages.append({
            "role":     "assistant",
            "content":  raw_response,
            "segments": segments,
        })
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.page == "home":
    render_home()
else:
    render_chat()
