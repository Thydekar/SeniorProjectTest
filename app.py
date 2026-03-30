import streamlit as st
import requests
import base64
import json
import re
import os
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
    "Assignment Generation": "Generate custom assignments, quizzes, and exercises.",
    "Assignment Grader":     "Grade submissions with rubric-based feedback.",
    "AI Content Detector":   "Detect AI-generated content with confidence scoring.",
    "Student Chatbot":       "An intelligent tutor for student questions.",
}
MODEL_ICONS = {
    "Assignment Generation": "⚡",
    "Assignment Grader":     "📊",
    "AI Content Detector":   "🔍",
    "Student Chatbot":       "🎓",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
TEXT_EXTS  = {
    ".txt",".js",".ts",".jsx",".tsx",".html",".htm",".css",
    ".py",".java",".c",".cpp",".h",".cs",".rb",".go",".rs",
    ".php",".md",".json",".xml",".yaml",".yml",".sh",".sql",
    ".swift",".kt",".r",".m",".pl",".lua",".dart",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spartan AI",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@300;400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #020c05 !important;
    color: #00ff88 !important;
    font-family: 'Rajdhani', sans-serif !important;
}

/* Grid BG */
[data-testid="stAppViewContainer"]::before {
    content:''; position:fixed; inset:0;
    background-image:
        linear-gradient(rgba(0,255,136,.04) 1px,transparent 1px),
        linear-gradient(90deg,rgba(0,255,136,.04) 1px,transparent 1px);
    background-size:44px 44px;
    pointer-events:none; z-index:0;
    animation:gp 9s ease-in-out infinite;
}
@keyframes gp{0%,100%{opacity:.45}50%{opacity:1}}

/* Scanlines */
[data-testid="stAppViewContainer"]::after {
    content:''; position:fixed; inset:0;
    background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.09) 2px,rgba(0,0,0,.09) 4px);
    pointer-events:none; z-index:1;
}

[data-testid="stMain"],.main{background:transparent !important;position:relative;z-index:2;}
[data-testid="stMainBlockContainer"]{padding:1rem 2rem 6rem !important;max-width:100% !important;}

/* Hide chrome */
#MainMenu,footer,header{visibility:hidden;}
[data-testid="stToolbar"],.stDeployButton,[data-testid="stDecoration"]{display:none !important;}

/* Scrollbar */
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-track{background:rgba(0,255,136,.03);}
::-webkit-scrollbar-thumb{background:rgba(0,255,136,.2);border-radius:2px;}

/* ── SIDEBAR ── */
[data-testid="stSidebar"]{
    background:rgba(0,6,2,.95) !important;
    border-right:1px solid rgba(0,255,136,.1) !important;
    backdrop-filter:blur(24px) !important;
}
[data-testid="stSidebar"] > div:first-child{padding-top:0 !important;}
[data-testid="stSidebarCollapseButton"] svg{stroke:#00ff88 !important;fill:rgba(0,255,136,.2) !important;}

/* Sidebar buttons */
section[data-testid="stSidebar"] .stButton > button {
    background:transparent !important;
    border:1px solid transparent !important;
    border-radius:9px !important;
    color:rgba(0,255,136,.5) !important;
    font-family:'Rajdhani',sans-serif !important;
    font-size:.93rem !important; font-weight:600 !important;
    letter-spacing:.03em !important;
    text-align:left !important;
    padding:8px 12px !important;
    width:100% !important;
    transition:all .16s !important;
    margin-bottom:2px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background:rgba(0,255,136,.07) !important;
    border-color:rgba(0,255,136,.2) !important;
    color:#00ff88 !important;
    box-shadow:0 0 12px rgba(0,255,136,.07) !important;
    transform:none !important;
}

/* ── MAIN BUTTONS ── */
.stButton > button {
    background:rgba(0,255,136,.07) !important;
    border:1px solid rgba(0,255,136,.28) !important;
    border-radius:10px !important;
    color:#00ff88 !important;
    font-family:'Rajdhani',sans-serif !important;
    font-weight:600 !important;
    letter-spacing:.05em !important;
    transition:all .18s !important;
}
.stButton > button:hover {
    background:rgba(0,255,136,.14) !important;
    border-color:rgba(0,255,136,.5) !important;
    box-shadow:0 0 16px rgba(0,255,136,.14) !important;
    transform:translateY(-1px) !important;
}

/* ── CHAT INPUT ── */
[data-testid="stChatInput"] > div {
    background:rgba(0,18,8,.85) !important;
    border:1px solid rgba(0,255,136,.22) !important;
    border-radius:13px !important;
    backdrop-filter:blur(20px) !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color:rgba(0,255,136,.5) !important;
    box-shadow:0 0 20px rgba(0,255,136,.09) !important;
}
[data-testid="stChatInput"] textarea {
    background:transparent !important;
    color:#00ff88 !important;
    font-family:'Rajdhani',sans-serif !important;
    font-size:1rem !important;
    caret-color:#00ff88 !important;
}
[data-testid="stChatInput"] button svg{stroke:#00ff88 !important;}

/* Bottom bar */
[data-testid="stBottom"]{
    background:rgba(2,12,5,.92) !important;
    backdrop-filter:blur(24px) !important;
    border-top:1px solid rgba(0,255,136,.09) !important;
}

/* ── CHAT MESSAGES ── */
[data-testid="stChatMessage"]{background:transparent !important;border:none !important;padding:4px 0 !important;}

/* Avatar icons */
[data-testid="chatAvatarIcon-user"] > div {
    background:rgba(0,255,136,.12) !important;
    border:1px solid rgba(0,255,136,.28) !important;
    color:#00ff88 !important;
}
[data-testid="chatAvatarIcon-assistant"] > div {
    background:rgba(0,255,136,.05) !important;
    border:1px solid rgba(0,255,136,.14) !important;
    color:#00ff88 !important;
}

/* Message text */
[data-testid="stChatMessage"] .stMarkdown p {
    color:#d0ffe8 !important;
    font-size:.97rem !important;
    line-height:1.68 !important;
}
[data-testid="stChatMessage"] .stMarkdown code {
    background:rgba(0,255,136,.08) !important;
    color:#00ff88 !important;
    border-radius:4px !important;
    font-family:'Share Tech Mono',monospace !important;
}
[data-testid="stChatMessage"] .stMarkdown pre {
    background:rgba(0,255,136,.04) !important;
    border:1px solid rgba(0,255,136,.14) !important;
    border-radius:8px !important;
}

/* File uploader in expander */
[data-testid="stFileUploaderDropzone"]{
    background:rgba(0,255,136,.03) !important;
    border:1px dashed rgba(0,255,136,.18) !important;
    border-radius:10px !important;
}
[data-testid="stFileUploaderDropzone"] span{color:rgba(0,255,136,.45) !important;}
[data-testid="stFileUploaderDropzone"] small{color:rgba(0,255,136,.28) !important;}

/* Expander */
[data-testid="stExpander"]{
    background:rgba(0,255,136,.02) !important;
    border:1px solid rgba(0,255,136,.12) !important;
    border-radius:10px !important;
}
[data-testid="stExpander"] summary{color:rgba(0,255,136,.55) !important;font-family:'Share Tech Mono',monospace !important;font-size:.82rem !important;}
[data-testid="stExpander"] summary svg{stroke:rgba(0,255,136,.4) !important;}

/* General markdown */
.stMarkdown p,.stMarkdown li{color:rgba(0,255,136,.72) !important;}
h1,h2,h3,h4{color:#00ff88 !important;font-family:'Share Tech Mono',monospace !important;}
hr{border-color:rgba(0,255,136,.1) !important;}

/* Spinner */
[data-testid="stSpinner"] > div{border-top-color:#00ff88 !important;}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_model_online(model_name: str) -> bool:
    try:
        r = requests.get(OLLAMA_TAGS_URL, auth=(USERNAME, PASSWORD), timeout=5)
        if r.status_code == 200:
            return any(t.get("name","").startswith(model_name)
                       for t in r.json().get("models", []))
    except Exception:
        pass
    return False


def stream_chat(model: str, messages: list):
    try:
        with requests.post(
            OLLAMA_CHAT_URL, auth=(USERNAME, PASSWORD),
            json={"model": model, "messages": messages, "stream": True},
            stream=True, timeout=120,
        ) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"\n[Connection error: {e}]"


def extract_text_from_image(file_bytes: bytes) -> str:
    try:
        return pytesseract.image_to_string(Image.open(io.BytesIO(file_bytes)), config=OCR_CONFIG)
    except Exception as e:
        return f"[OCR error: {e}]"


def strip_output_tags(text: str) -> str:
    text = re.sub(r'\[/?output-text\]', '', text)
    text = re.sub(r'\[output-file-[^\]]+\].*?\[/output-file-[^\]]+\]', '[generating file...]', text, flags=re.DOTALL)
    return text.strip()


def parse_output_blocks(raw: str):
    parts = []
    file_pat = re.compile(r'\[output-file-(\w+)-([^\]]+)\](.*?)\[/output-file-\1-\2\]', re.DOTALL)
    text_pat  = re.compile(r'\[output-text\](.*?)\[/output-text\]', re.DOTALL)
    spans = []
    for m in text_pat.finditer(raw):
        spans.append(("text", m.start(), m.end(), m.group(1).strip()))
    for m in file_pat.finditer(raw):
        spans.append(("file", m.start(), m.end(), m.group(3).strip(), m.group(1), m.group(2)))
    spans.sort(key=lambda x: x[1])
    for s in spans:
        if s[0] == "text":
            parts.append({"type":"text","content":s[3]})
        else:
            parts.append({"type":"file","content":s[3],"ext":s[4],"filename":s[5]})
    if not parts and raw.strip():
        parts.append({"type":"text","content":strip_output_tags(raw)})
    return parts


def render_file_widget(fname: str, ext: str, content: str):
    raw_bytes = content.encode("utf-8")
    b64 = base64.b64encode(raw_bytes).decode()
    st.markdown(f"""
    <a href="data:text/plain;base64,{b64}" download="{fname}.{ext}" style="text-decoration:none;">
        <div style="display:inline-flex;align-items:center;gap:12px;
                    background:rgba(0,255,136,.06);border:1px solid rgba(0,255,136,.25);
                    border-radius:11px;padding:11px 18px;color:#00ff88;
                    font-family:'Share Tech Mono',monospace;font-size:.8rem;
                    cursor:pointer;margin-top:6px;">
            <span style="font-size:1.3rem;">📄</span>
            <div>
                <div style="font-weight:700;">{fname}.{ext}</div>
                <div style="opacity:.5;font-size:.7rem;margin-top:2px;">Click to download generated file</div>
            </div>
            <span style="margin-left:16px;font-size:1.1rem;">⬇</span>
        </div>
    </a>
    """, unsafe_allow_html=True)


def build_ollama_messages(chat_history: list, model_display: str) -> list:
    msgs = [{"role":"system","content":(
        f"You are Spartan AI — the {model_display} module. "
        "Wrap ALL text responses in [output-text]...[/output-text]. "
        "For generated files use [output-file-ext-filename]...[/output-file-ext-filename]. "
        "Be helpful, precise, and educational."
    )}]
    for h in chat_history:
        msgs.append({"role":"user" if h["role"]=="user" else "assistant",
                     "content":h.get("_raw", h["content"])})
    return msgs


def status_dot(online: bool) -> str:
    c = "#00ff88" if online else "#ff3355"
    lbl = "ONLINE" if online else "OFFLINE"
    anim = "animation:gp 2s infinite;" if online else ""
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;">'
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{c};box-shadow:0 0 7px {c};{anim}"></span>'
            f'<span style="font-family:\'Share Tech Mono\',monospace;font-size:.7rem;color:{c};">{lbl}</span>'
            f'</span>')


# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "page":"home","active_model":None,"chat_history":[],
    "pending_file":None,"model_status":{},"upload_key":0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.model_status:
    for dn, mid in MODEL_MAP.items():
        st.session_state.model_status[dn] = check_model_online(mid)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:22px 6px 14px;text-align:center;">
        <div style="font-family:'Share Tech Mono',monospace;font-size:1.25rem;
                    color:#00ff88;letter-spacing:.22em;
                    text-shadow:0 0 20px rgba(0,255,136,.5);">⚔ SPARTAN</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;
                    color:rgba(0,255,136,.28);letter-spacing:.28em;margin-top:3px;">
            EDUCATION AI
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if st.button("🏠  Home", key="sb_home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;font-size:.62rem;
                color:rgba(0,255,136,.22);letter-spacing:.22em;padding:14px 4px 5px;">
        TOOLS
    </div>
    """, unsafe_allow_html=True)

    for dname in MODEL_MAP:
        online = st.session_state.model_status.get(dname, False)
        dot_c  = "#00ff88" if online else "#ff3355"
        icon   = MODEL_ICONS[dname]
        col_btn, col_dot = st.columns([6, 1])
        with col_btn:
            if st.button(f"{icon}  {dname}", key=f"sb_{dname}", use_container_width=True):
                st.session_state.page = "chat"
                st.session_state.active_model = dname
                st.session_state.pending_file = None
                st.rerun()
        with col_dot:
            st.markdown(
                f'<div style="height:36px;display:flex;align-items:center;justify-content:center;">'
                f'<div style="width:8px;height:8px;border-radius:50%;'
                f'background:{dot_c};box-shadow:0 0 6px {dot_c};"></div></div>',
                unsafe_allow_html=True
            )

    st.divider()

    if st.session_state.page == "chat" and st.session_state.active_model:
        if st.button("＋  New Chat", key="sb_newchat", use_container_width=True):
            st.session_state.chat_history  = []
            st.session_state.pending_file  = None
            st.session_state.upload_key   += 1
            st.rerun()

    if st.button("↺  Refresh Status", key="sb_refresh", use_container_width=True):
        for dn, mid in MODEL_MAP.items():
            st.session_state.model_status[dn] = check_model_online(mid)
        st.rerun()

    st.markdown("""
    <div style="position:absolute;bottom:18px;left:0;right:0;text-align:center;
                font-family:'Share Tech Mono',monospace;font-size:.58rem;
                color:rgba(0,255,136,.16);letter-spacing:.12em;">
        v1.0 · DALLIN GEURTS
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_home():
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    col = st.columns([1, 3, 1])[1]
    with col:
        st.markdown("""
        <div style="text-align:center;padding:28px 0 18px;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:.68rem;
                        color:rgba(0,255,136,.3);letter-spacing:.35em;margin-bottom:10px;">
                ⚔ &nbsp; EDUCATION INTELLIGENCE PLATFORM &nbsp; ⚔
            </div>
            <div style="font-family:'Share Tech Mono',monospace;
                        font-size:clamp(2.4rem,5.5vw,4rem);color:#00ff88;
                        text-shadow:0 0 26px rgba(0,255,136,.5),0 0 70px rgba(0,255,136,.1);
                        letter-spacing:.16em;">
                SPARTAN AI
            </div>
            <div style="font-size:1rem;color:rgba(0,255,136,.45);
                        letter-spacing:.07em;margin-top:7px;font-weight:300;">
                Built by Dallin Geurts &nbsp;·&nbsp; Empowering Teachers &amp; Students
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown("""
    <p style="text-align:center;max-width:580px;margin:0 auto 26px;
              font-size:.97rem;color:rgba(0,255,136,.42);line-height:1.85;">
        A suite of specialized AI tools designed to streamline every aspect of education —
        generating assignments, grading submissions, detecting AI-written content,
        and giving every student an intelligent personal tutor.<br><br>
        Select a tool from the sidebar, or launch one below.
    </p>
    """, unsafe_allow_html=True)

    cols = st.columns(2, gap="large")
    for idx, (dname, mid) in enumerate(MODEL_MAP.items()):
        online = st.session_state.model_status.get(dname, False)
        dot_c  = "#00ff88" if online else "#ff3355"
        lbl    = "ONLINE" if online else "OFFLINE"
        with cols[idx % 2]:
            st.markdown(f"""
            <div style="background:rgba(0,255,136,.025);border:1px solid rgba(0,255,136,.12);
                        border-radius:14px;padding:22px 20px 18px;margin-bottom:8px;">
                <div style="font-size:1.8rem;margin-bottom:8px;">{MODEL_ICONS[dname]}</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:.87rem;
                            color:#00ff88;letter-spacing:.06em;margin-bottom:6px;">
                    {dname.upper()}
                </div>
                <div style="font-size:.84rem;color:rgba(0,255,136,.42);
                            line-height:1.55;margin-bottom:14px;">
                    {MODEL_DESCRIPTIONS[dname]}
                </div>
                <div style="display:flex;align-items:center;gap:7px;">
                    <div style="width:7px;height:7px;border-radius:50%;
                                background:{dot_c};box-shadow:0 0 6px {dot_c};"></div>
                    <span style="font-family:'Share Tech Mono',monospace;
                                 font-size:.68rem;color:{dot_c};">{lbl}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Launch {dname} →", key=f"home_{idx}", use_container_width=True):
                st.session_state.page = "chat"
                st.session_state.active_model = dname
                st.session_state.chat_history = []
                st.session_state.pending_file = None
                st.rerun()
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT PAGE
# ══════════════════════════════════════════════════════════════════════════════
def render_chat():
    display_name = st.session_state.active_model
    model_id     = MODEL_MAP[display_name]
    online       = st.session_state.model_status.get(display_name, False)
    dot_c        = "#00ff88" if online else "#ff3355"
    lbl          = "ONLINE" if online else "OFFLINE"

    # Page header
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;
                padding:8px 0 14px;border-bottom:1px solid rgba(0,255,136,.09);
                margin-bottom:14px;">
        <span style="font-size:1.35rem;">{MODEL_ICONS[display_name]}</span>
        <span style="font-family:'Share Tech Mono',monospace;font-size:.97rem;
                     color:#00ff88;letter-spacing:.1em;">{display_name.upper()}</span>
        <div style="margin-left:auto;display:flex;align-items:center;gap:7px;">
            <div style="width:8px;height:8px;border-radius:50%;
                        background:{dot_c};box-shadow:0 0 8px {dot_c};"></div>
            <span style="font-family:'Share Tech Mono',monospace;
                         font-size:.7rem;color:{dot_c};">{lbl}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pending file banner
    pf = st.session_state.pending_file
    if pf:
        c1, c2 = st.columns([9, 1])
        with c1:
            st.markdown(f"""
            <div style="background:rgba(0,255,136,.05);border:1px dashed rgba(0,255,136,.22);
                        border-radius:9px;padding:7px 14px;margin-bottom:8px;
                        font-family:'Share Tech Mono',monospace;font-size:.76rem;
                        color:rgba(0,255,136,.6);">
                📎 &nbsp;<strong>{pf['label']}</strong>
                &nbsp;— <em style="opacity:.7;">will be sent with your next message</em>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            if st.button("✕", key="rm_pf", help="Remove attachment"):
                st.session_state.pending_file = None
                st.session_state.upload_key  += 1
                st.rerun()

    # ── Chat history ──
    for msg in st.session_state.chat_history:
        role    = msg["role"]
        content = msg["content"]
        fl      = msg.get("file_label")

        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
                if fl:
                    st.markdown(
                        f'<div style="display:inline-block;margin-top:5px;'
                        f'background:rgba(0,255,136,.05);'
                        f'border:1px dashed rgba(0,255,136,.18);'
                        f'border-radius:8px;padding:4px 12px;'
                        f'font-family:\'Share Tech Mono\',monospace;'
                        f'font-size:.73rem;color:rgba(0,255,136,.5);">📎 {fl}</div>',
                        unsafe_allow_html=True
                    )
        else:
            with st.chat_message("assistant", avatar="⚔"):
                blocks = parse_output_blocks(content)
                for block in blocks:
                    if block["type"] == "text":
                        st.markdown(block["content"])
                    else:
                        render_file_widget(block["filename"], block["ext"], block["content"])

    # ── File attach expander ──
    with st.expander("📎  Attach a file to next message", expanded=False):
        uploaded = st.file_uploader(
            "Drag & drop or browse — images and text files only",
            key=f"fu_{st.session_state.upload_key}",
            type=[
                "png","jpg","jpeg","gif","bmp","tiff","webp",
                "txt","js","ts","jsx","tsx","html","htm","css",
                "py","java","c","cpp","h","cs","rb","go","rs",
                "php","md","json","xml","yaml","yml","sh","sql",
                "swift","kt","r","m","pl","lua","dart",
            ],
            label_visibility="visible",
        )
        if uploaded is not None and (pf is None or pf.get("_fname") != uploaded.name):
            name = uploaded.name
            ext  = os.path.splitext(name)[1].lower()
            raw  = uploaded.read()
            if ext in IMAGE_EXTS:
                ocr = extract_text_from_image(raw)
                tag = f"[input-file-image-text]\n{ocr}\n[/input-file-image-text]"
                lbl_text = f"{name} (image → OCR)"
            else:
                txt = raw.decode("utf-8", errors="replace")
                ft  = ext.lstrip(".") or "txt"
                tag = f"[input-file-{ft}-text]\n{txt}\n[/input-file-{ft}-text]"
                lbl_text = name
            st.session_state.pending_file = {"label": lbl_text, "tag": tag, "_fname": name}
            st.session_state.upload_key  += 1
            st.rerun()

    # ── Chat input ──
    user_text = st.chat_input(placeholder=f"Message {display_name}...")

    if user_text:
        pf         = st.session_state.pending_file
        file_label = None
        composed   = f"[input-user-text]\n{user_text}\n[/input-user-text]"

        if pf:
            file_label = pf["label"]
            composed   = pf["tag"] + "\n\n" + composed
            st.session_state.pending_file = None
            st.session_state.upload_key  += 1

        st.session_state.chat_history.append({
            "role":"user","content":user_text,
            "file_label":file_label,"_raw":composed,
        })

        # Show user bubble immediately
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_text)
            if file_label:
                st.markdown(
                    f'<div style="display:inline-block;margin-top:5px;'
                    f'background:rgba(0,255,136,.05);'
                    f'border:1px dashed rgba(0,255,136,.18);'
                    f'border-radius:8px;padding:4px 12px;'
                    f'font-family:\'Share Tech Mono\',monospace;'
                    f'font-size:.73rem;color:rgba(0,255,136,.5);">📎 {file_label}</div>',
                    unsafe_allow_html=True
                )

        # Stream AI response
        ollama_msgs = build_ollama_messages(st.session_state.chat_history, display_name)
        with st.chat_message("assistant", avatar="⚔"):
            full_response = ""
            placeholder   = st.empty()
            for chunk in stream_chat(model_id, ollama_msgs):
                full_response += chunk
                # Show clean live text with blinking cursor character
                placeholder.markdown(strip_output_tags(full_response) + " ▌")
            placeholder.empty()

            # Final parsed render
            blocks = parse_output_blocks(full_response)
            for block in blocks:
                if block["type"] == "text":
                    st.markdown(block["content"])
                else:
                    render_file_widget(block["filename"], block["ext"], block["content"])

        st.session_state.chat_history.append({"role":"ai","content":full_response})


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "chat":
    render_chat()
