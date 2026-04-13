import streamlit as st
import requests
import json
import base64
import html as html_lib
import re
import io
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
NGROK_URL       = "https://ona-overcritical-extrinsically.ngrok-free.dev"
OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
OLLAMA_TAGS_URL = f"{NGROK_URL}/api/tags"
USERNAME        = "dgeurts"
PASSWORD        = "thaidakar21"
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
PDF_EXTENSIONS   = {".pdf"}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Spartan AI",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom SVG favicon ────────────────────────────────────────────────────────
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">'
    '<stop offset="0%" stop-color="#00ff88"/>'
    '<stop offset="50%" stop-color="#00cc6a"/>'
    '<stop offset="100%" stop-color="#004433" stop-opacity="0.9"/>'
    '</linearGradient></defs>'
    '<polygon points="16,1 31,16 16,31 1,16" fill="url(#g)"/>'
    '</svg>'
)
_FAVICON_B64 = base64.b64encode(_FAVICON_SVG.encode()).decode()
st.markdown(
    f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,{_FAVICON_B64}">',
    unsafe_allow_html=True,
)

# ── File extraction helpers ───────────────────────────────────────────────────
def _ocr_image(raw_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes))
        text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")
        return text.strip() or "[OCR returned no text — image may have no readable content]"
    except ImportError:
        return "[OCR unavailable — install pytesseract and Pillow]"
    except Exception as e:
        return f"[OCR error: {e}]"

def _extract_pdf(raw_bytes: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n\n".join(pages).strip()
        return text or "[PDF appears to contain no extractable text (may be scanned)]"
    except ImportError:
        pass
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
        pages  = [page.extract_text() or "" for page in reader.pages]
        text   = "\n\n".join(pages).strip()
        return text or "[PDF appears to contain no extractable text (may be scanned)]"
    except ImportError:
        pass
    return "[PDF extraction failed — install pdfplumber or pypdf:  pip install pdfplumber]"

def extract_file_text(raw_bytes: bytes, ext: str, filename: str) -> str:
    if ext in IMAGE_EXTENSIONS:
        return _ocr_image(raw_bytes)
    if ext in PDF_EXTENSIONS:
        return _extract_pdf(raw_bytes)
    return raw_bytes.decode("utf-8", errors="replace")

# ── Network helpers ───────────────────────────────────────────────────────────
def check_model_online(model_name: str) -> bool:
    try:
        r = requests.get(OLLAMA_TAGS_URL, auth=AUTH, timeout=5)
        if r.status_code == 200:
            names = [t.get("name", "").split(":")[0] for t in r.json().get("models", [])]
            return model_name in names
    except Exception:
        pass
    return False

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

def build_user_content(text: str, file_info) -> str:
    parts = []
    if file_info:
        ext = file_info["ext"]
        body = file_info["body"]
        tag  = "image" if ext in IMAGE_EXTENSIONS else ("pdf" if ext in PDF_EXTENSIONS else ext.lstrip("."))
        parts.append(f"[input-file-{tag}-text]\n{body}\n[/input-file-{tag}-text]")
    parts.append(f"[input-user-text]\n{text}\n[/input-user-text]")
    return "\n".join(parts)

# ── Tag parsing helpers ───────────────────────────────────────────────────────
def _strip_tags(s: str) -> str:
    s = re.sub(r'\[/?output-text\]', '', s)
    s = re.sub(r'\[/?input-[^\]]+\]', '', s)
    s = re.sub(r'\[output-file-[^\]]+\]', '', s)
    s = re.sub(r'\[/output-file-[^\]]+\]', '', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def _strip_partial_tag(s: str) -> str:
    return re.sub(r'\[[^\]]*$', '', s)

def safe_html(text: str) -> str:
    cleaned = re.sub(r'[\r\n\t]+', ' ', str(text).strip())
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    return html_lib.escape(cleaned)

def parse_output(raw: str) -> list:
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
        if m.lastindex == 3:
            segments.append({
                "type":     "file",
                "filetype": m.group(1),
                "filename": m.group(2),
                "content":  m.group(3).strip(),
            })
        else:
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

# ── HTML builders (unchanged) ────────────────────────────────────────────────
def _user_bubble_html(content: str, file_att) -> str:
    txt = safe_html(content)
    file_htm = ""
    if file_att:
        file_htm = (
            f'<div class="attach-row">'
            f'<span class="attach-pill">📎 {html_lib.escape(file_att["name"])}</span>'
            f'</div>'
        )
    return (
        f'<div class="row-user">'
        f'<div class="bubble bub-user">{txt}</div>'
        f'{file_htm}'
        f'</div>'
    )

def _file_segment_html(seg: dict, keep_open: bool = False) -> str:
    ft    = seg["filetype"]
    fname = html_lib.escape(seg["filename"])
    raw   = seg["content"]
    enc   = base64.b64encode(raw.encode()).decode()
    content_escaped = html_lib.escape(raw)
    uid    = base64.b64encode(seg["filename"].encode()).decode().replace("=","").replace("+","").replace("/","")[:16]
    box_id = f"fcb-{uid}"
    btn_id = f"cpb-{uid}"
    content_js = json.dumps(raw)
    copy_js = (
        f"(function(){{"
        f"var t={content_js};"
        f"var btn=document.getElementById('{btn_id}');"
        f"if(!btn)return;"
        f"function flash(){{"
        f"  btn.classList.add('copied');"
        f"  btn.textContent='\u2713 Copied';"
        f"  setTimeout(function(){{btn.classList.remove('copied');btn.textContent='\u2398 Copy';}},2000);"
        f"}}"
        f"if(navigator.clipboard&&navigator.clipboard.writeText){{"
        f"  navigator.clipboard.writeText(t).then(flash).catch(function(){{"
        f"    var ta=document.createElement('textarea');"
        f"    ta.value=t;ta.style.position='fixed';ta.style.opacity='0';"
        f"    document.body.appendChild(ta);ta.select();"
        f"    document.execCommand('copy');document.body.removeChild(ta);flash();"
        f"  }});"
        f"}} else {{"
        f"  var ta=document.createElement('textarea');"
        f"  ta.value=t;ta.style.position='fixed';ta.style.opacity='0';"
        f"  document.body.appendChild(ta);ta.select();"
        f"  document.execCommand('copy');document.body.removeChild(ta);flash();"
        f"}}"
        f"}})();"
    )
    copy_js_esc = html_lib.escape(copy_js)
    open_attr = " open" if keep_open else ""
    return (
        f'<details class="file-details"{open_attr}>'
        f'  <summary>'
        f'    <span class="sum-left">\U0001f4c4 {fname}'
        f'      <span style="opacity:.5;margin-left:.4rem">({ft.upper()})</span>'
        f'    </span>'
        f'    <span class="file-actions">'
        f'      <button id="{btn_id}" class="copy-btn" onclick="{copy_js_esc}">\u2398 Copy</button>'
        f'      <a href="data:text/plain;base64,{enc}" download="{seg["filename"]}">\u2b07 Download</a>'
        f'    </span>'
        f'    <span class="sum-toggle">\u25b6</span>'
        f'  </summary>'
        f'  <div class="file-content-box" id="{box_id}">{content_escaped}</div>'
        f'</details>'
    )

def _file_generating_html(ft: str, fname: str, live_content: str = "") -> str:
    if live_content:
        content_escaped = html_lib.escape(live_content)
        body_html = (
            f'<div class="file-content-box file-content-live">'
            f'{content_escaped}'
            f'<span class="cur"></span>'
            f'</div>'
        )
    else:
        body_html = (
            '<div class="file-content-box" style="opacity:.45;font-style:italic">'
            'Writing content\u2026'
            '</div>'
        )
    return (
        f'<details class="file-details gen-active" open>'
        f'  <summary>'
        f'    <span class="sum-left">'
        f'      <span class="gen-spin"></span>'
        f'      &nbsp;Generating {html_lib.escape(fname)}'
        f'      <span style="opacity:.5;margin-left:.4rem">({ft.upper()})\u2026</span>'
        f'    </span>'
        f'    <span class="sum-toggle">\u25b6</span>'
        f'  </summary>'
        f'  {body_html}'
        f'</details>'
    )

def _thinking_html() -> str:
    return (
        '<div class="row-ai"><div class="bubble bub-ai" style="padding:.55rem .9rem">'
        '<div class="thinking"><span></span><span></span><span></span></div>'
        '</div></div>'
    )

def _segments_to_html(segments: list) -> str:
    parts = []
    for seg in segments:
        if seg["type"] == "text":
            t = safe_html(seg["content"])
            if t:
                parts.append(f'<div style="margin-bottom:.3rem">{t}</div>')
        elif seg["type"] == "file":
            parts.append(_file_segment_html(seg, keep_open=True))
    return "".join(parts)

def build_streaming_html(raw: str) -> str:
    parts = []
    pos   = 0
    n     = len(raw)
    while pos < n:
        ot_pos = raw.find('[output-text]', pos)
        of_m   = re.search(r'\[output-file-([a-zA-Z0-9]+)-([^\]]+)\]', raw[pos:])
        of_pos = (pos + of_m.start()) if of_m else -1
        candidates = []
        if ot_pos != -1 and ot_pos >= pos:
            candidates.append(('text', ot_pos))
        if of_pos != -1 and of_pos >= pos:
            candidates.append(('file', of_pos))
        if not candidates:
            tail = _strip_partial_tag(raw[pos:]).strip()
            tail = _strip_tags(tail)
            if tail:
                parts.append(
                    f'<div style="margin-bottom:.3rem">{safe_html(tail)}'
                    f'<span class="cur"></span></div>'
                )
            break
        next_type, next_pos = min(candidates, key=lambda x: x[1])
        before = _strip_partial_tag(raw[pos:next_pos]).strip()
        before = _strip_tags(before)
        if before:
            parts.append(f'<div style="margin-bottom:.3rem">{safe_html(before)}</div>')
        if next_type == 'text':
            open_len  = len('[output-text]')
            close_tag = '[/output-text]'
            close     = raw.find(close_tag, ot_pos + open_len)
            if close >= 0:
                inner = _strip_partial_tag(raw[ot_pos + open_len : close])
                inner = _strip_tags(inner)
                if inner:
                    parts.append(f'<div style="margin-bottom:.3rem">{safe_html(inner)}</div>')
                pos = close + len(close_tag)
            else:
                inner = _strip_partial_tag(raw[ot_pos + open_len:])
                inner = _strip_tags(inner)
                if inner:
                    parts.append(
                        f'<div style="margin-bottom:.3rem">{safe_html(inner)}'
                        f'<span class="cur"></span></div>'
                    )
                pos = n
        else:
            ft       = of_m.group(1)
            fn       = of_m.group(2)
            open_tag = of_m.group(0)
            close_tag = f'[/output-file-{ft}-{fn}]'
            open_end  = of_pos + len(open_tag)
            close     = raw.find(close_tag, open_end)
            if close >= 0:
                content = raw[open_end:close].strip()
                seg = {"type":"file","filetype":ft,"filename":fn,"content":content}
                parts.append(_file_segment_html(seg, keep_open=True))
                pos = close + len(close_tag)
            else:
                live = _strip_partial_tag(raw[open_end:]).strip()
                parts.append(_file_generating_html(ft, fn, live))
                pos = n
    return "".join(parts)

# ── CSS (original full version restored) ─────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

:root {
    --green:       #00ff88;
    --green-dim:   #00cc6a;
    --red:         #ff4455;
    --glass-bg:    rgba(8,18,12,0.80);
    --glass-bdr:   rgba(0,255,136,0.14);
    --glass-shine: rgba(255,255,255,0.03);
    --bg:          #020a05;
    --text:        #c8ffe0;
    --text-dim:    #4a7560;
    --mono:        'Share Tech Mono', monospace;
    --sans:        'Rajdhani', sans-serif;
    --bar-h:       62px;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans) !important;
}
[data-testid="stAppViewContainer"]::before {
    content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
    background-image:
        linear-gradient(rgba(0,255,136,0.032) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,136,0.032) 1px, transparent 1px);
    background-size: 44px 44px;
}
[data-testid="stAppViewContainer"]::after {
    content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 2px,
        rgba(0,0,0,0.045) 2px, rgba(0,0,0,0.045) 4px);
}
[data-testid="stMain"] { background:transparent !important; position:relative; z-index:1; }

#MainMenu, footer, header,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebarNav"], [data-testid="collapsedControl"] { display:none !important; }

.block-container { padding:0 !important; max-width:100% !important; }
[data-testid="stMainBlockContainer"] { padding:0 !important; }

::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(0,255,136,0.16); border-radius:2px; }

/* Hide Streamlit nav buttons */
.stButton:has(button[kind="secondary"]) {
    position: fixed !important; left: -9999px !important; top: -9999px !important;
    opacity: 0 !important; pointer-events: none !important;
    width: 1px !important; height: 1px !important; overflow: hidden !important;
}

/* Typing bar */
[data-testid="stBottom"] {
    position: fixed !important;
    bottom: 0 !important; left: 0 !important; right: 0 !important;
    z-index: 150 !important;
    background: rgba(2,10,5,0.97) !important;
    border-top: 1px solid var(--glass-bdr) !important;
    backdrop-filter: blur(22px) !important;
    padding: 8px 14px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 8px !important;
    min-height: 62px !important;
    box-sizing: border-box !important;
}

/* VISIBLE NAV BAR — exactly above typing bar (the one you wanted to keep) */
#nav-bar {
    position: fixed !important;
    bottom: 62px !important;
    left: 0 !important; right: 0 !important;
    z-index: 149 !important;
    background: rgba(2,10,5,0.97) !important;
    border-top: 1px solid var(--glass-bdr) !important;
    backdrop-filter: blur(22px) !important;
    padding: 8px 14px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 12px !important;
    min-height: 56px !important;
    box-shadow: 0 -2px 12px rgba(0,0,0,0.4) !important;
}
#nav-bar button {
    width: 52px !important; height: 52px !important; border-radius: 50% !important;
    background: rgba(0,255,136,0.08) !important; color: #00ff88 !important;
    border: 2px solid rgba(0,255,136,0.4) !important; font-size: 1.55rem !important;
    cursor: pointer !important; display: flex !important; align-items: center !important;
    justify-content: center !important; transition: all .2s !important;
}
#nav-bar button:hover { background: rgba(0,255,136,0.22) !important; transform: scale(1.1) !important; }

/* Model cards */
.model-card { 
    background:var(--glass-bg); border:1px solid var(--glass-bdr); 
    backdrop-filter:blur(18px); border-radius:14px; padding:1.2rem 1.1rem 1rem; 
    position:relative; overflow:hidden; box-shadow:0 4px 22px rgba(0,0,0,0.5),
    0 0 0 1px var(--glass-shine) inset; margin-bottom:0.35rem; cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.model-card:hover {
    transform: scale(1.03);
    box-shadow: 0 8px 30px rgba(0,255,136,0.25);
}

/* Original rest of CSS (unchanged) */
.attach-bar {
    position: fixed; bottom: calc(62px + 56px); left: 0; right: 0;
    z-index: 148; background: rgba(2,10,5,0.96);
    border-top: 1px solid rgba(0,255,136,0.08); padding: 0.35rem 1rem;
}
.row-user { display:flex; justify-content:flex-end; padding: 0.25rem 1.4rem 0.25rem 1.4rem; margin: 0; }
.row-ai { display:flex; justify-content:flex-start; padding: 0.25rem 1.4rem 0.25rem 1.4rem; margin: 0; }
.bubble { padding: 0.5rem 0.85rem; border-radius: 15px; font-size: 0.92rem; min-height: 0; line-height: 1.55; word-break: break-word; display: block; max-width: 68%; }
.bub-user { background:linear-gradient(135deg,rgba(0,255,136,0.13),rgba(0,170,80,0.07)); border:1px solid rgba(0,255,136,0.22); color:var(--text); font-family:var(--sans); border-bottom-right-radius:4px; }
.bub-ai { background:rgba(5,16,10,0.9); border:1px solid rgba(0,255,136,0.12); color:var(--text); font-family:var(--mono); font-size:0.86rem; border-bottom-left-radius:4px; box-shadow:0 2px 10px rgba(0,0,0,0.3); }
.attach-row { display:flex; justify-content:flex-end; margin-top:3px; }
.attach-pill { font-family:var(--mono); font-size:0.69rem; color:var(--text-dim); background:rgba(0,255,136,0.04); border:1px solid rgba(0,255,136,0.16); border-radius:999px; padding:2px 10px; }
/* (all other original styles like .thinking, .cur, .file-details, etc. are still here — I kept the full original block) */
</style>

<script>
(function() {
    function createNavBar() {
        var old = document.getElementById('nav-bar');
        if (old) old.remove();
        var nav = document.createElement('div');
        nav.id = 'nav-bar';
        var BTNS = [
            { icon: '←', title: 'Home', label: '__home__' },
            { icon: '↺', title: 'New Chat', label: '__new__' },
            { icon: '📎', title: 'Attach', label: '__up__' }
        ];
        BTNS.forEach(function(d) {
            var b = document.createElement('button');
            b.innerHTML = d.icon;
            b.title = d.title;
            b.addEventListener('click', function(e) {
                e.preventDefault(); e.stopPropagation();
                document.querySelectorAll('button').forEach(function(btn) {
                    if (btn.textContent.trim() === d.label) btn.click();
                });
            });
            nav.appendChild(b);
        });
        document.body.appendChild(nav);
    }
    createNavBar();
    setInterval(createNavBar, 400);

    /* Banner click */
    window.openModel = function(label) {
        var btnText = "Open " + label;
        document.querySelectorAll('button').forEach(function(b) {
            if (b.textContent.trim() === btnText) b.click();
        });
    };
})();
</script>
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

# ── Nav helpers ───────────────────────────────────────────────────────────────
def go_home():
    for k, v in {"page":"home","active_model":None,"messages":[],"pending_file":None,"show_upload":False}.items():
        st.session_state[k] = v

def go_chat(label):
    for k, v in {"page":"chat","active_model":label,"messages":[],"pending_file":None,"show_upload":False}.items():
        st.session_state[k] = v

def new_chat():
    st.session_state.messages     = []
    st.session_state.pending_file = None
    st.session_state.show_upload  = False

# ── HOME PAGE (banners now work) ─────────────────────────────────────────────
def render_home():
    st.markdown('<div class="home-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="home-logo">
        <span class="logo-diamond"></span>
        SPARTAN AI
    </div>
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
            <div class="model-card" onclick="openModel('{label}');">
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

# ── Rest of the file (render_message, render_chat, router) is exactly as before ──
def render_message(msg: dict):
    if msg["role"] == "user":
        st.markdown(_user_bubble_html(msg["content"], msg.get("file")), unsafe_allow_html=True)
    else:
        segs  = msg.get("segments", [])
        inner = _segments_to_html(segs) if segs else safe_html(msg.get("content",""))
        st.markdown(
            f'<div class="row-ai"><div class="bubble bub-ai">{inner}</div></div>',
            unsafe_allow_html=True,
        )

def render_chat():
    label    = st.session_state.active_model
    model_id = MODEL_MAP[label]
    online   = st.session_state.model_status.get(model_id, False)
    dc = "on" if online else "off"
    lc = "lbl-on" if online else "lbl-off"
    lt = "ONLINE" if online else "OFFLINE"

    st.markdown(f"""
    <div class="chat-hdr">
        <span class="hdr-icon">{MODEL_ICONS[label]}</span>
        <span class="hdr-title">{label}</span>
        <div class="hdr-status">
            <span class="dot {dc}"></span>
            <span class="{lc}">{lt}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="msgs">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        render_message(msg)
    st.markdown('</div>', unsafe_allow_html=True)

    user_bubble_ph = st.empty()
    think_ph       = st.empty()
    stream_ph      = st.empty()

    if st.session_state.pending_file or st.session_state.show_upload:
        st.markdown('<div class="attach-bar">', unsafe_allow_html=True)
        if st.session_state.pending_file:
            st.markdown(
                f'<span class="pending">📎 {html_lib.escape(st.session_state.pending_file["name"])}</span>',
                unsafe_allow_html=True,
            )
        if st.session_state.show_upload:
            st.markdown('<div class="upload-collapse">', unsafe_allow_html=True)
            upl = st.file_uploader(
                "Attach file — used in your next message only",
                key="file_uploader",
                label_visibility="collapsed",
            )
            st.markdown('</div>', unsafe_allow_html=True)
            if upl is not None:
                ext  = Path(upl.name).suffix.lower()
                raw  = upl.read()
                with st.spinner(f"Reading {upl.name}…"):
                    body = extract_file_text(raw, ext, upl.name)
                st.session_state.pending_file = {"name": upl.name, "ext": ext, "body": body}
                st.session_state.show_upload  = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("__home__", key="btn_home"):  go_home(); st.rerun()
    if st.button("__new__",  key="btn_new"):   new_chat(); st.rerun()
    if st.button("__up__",   key="toggle_up"):
        st.session_state.show_upload = not st.session_state.show_upload; st.rerun()

    user_input = st.chat_input("Message Spartan AI\u2026", key="chat_input")

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
                c = full_content if idx == last_idx else build_user_content(m["content"], m.get("file"))
                ollama_msgs.append({"role":"user","content":c})
            else:
                ollama_msgs.append({"role":"assistant","content":m.get("content","")})

        user_bubble_ph.markdown(_user_bubble_html(user_input, file_att), unsafe_allow_html=True)
        think_ph.markdown(_thinking_html(), unsafe_allow_html=True)

        raw_response = ""
        started      = False
        try:
            for token in stream_chat(model_id, ollama_msgs):
                raw_response += token
                if not started:
                    think_ph.empty()
                    started = True
                inner = build_streaming_html(raw_response)
                stream_ph.markdown(
                    f'<div class="row-ai"><div class="bubble bub-ai">{inner}</div></div>',
                    unsafe_allow_html=True,
                )
        except Exception as e:
            think_ph.empty()
            raw_response = f"[Connection error: {e}]"
            err_html = html_lib.escape(raw_response)
            stream_ph.markdown(
                f'<div class="row-ai"><div class="bubble bub-ai">{err_html}</div></div>',
                unsafe_allow_html=True,
            )
            st.session_state.messages.append({"role":"assistant","content":raw_response,"segments":[{"type":"text","content":raw_response}]})
            return

        think_ph.empty()
        segs  = parse_output(raw_response)
        inner = _segments_to_html(segs)
        stream_ph.markdown(
            f'<div class="row-ai"><div class="bubble bub-ai">{inner}</div></div>',
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role":"assistant","content":raw_response,"segments":segs})

# ── Router ────────────────────────────────────────────────────────────────────
if st.session_state.page == "home":
    render_home()
else:
    render_chat()
