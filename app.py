# app.py — Spartan AI (v2)
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

# ── Config ─────────────────────────────────────────────────────────────────────
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

TOOL_META = {
    "Assignment Generation": {
        "tag": "GEN", "index": "01", "color": "#00c8ff", "icon": "✦",
        "desc": "Generate custom assignments, rubrics, and prompts for any subject or grade.",
    },
    "Assignment Grader": {
        "tag": "GRD", "index": "02", "color": "#38e8c0", "icon": "◈",
        "desc": "Upload student work and receive detailed rubric-aligned grading feedback.",
    },
    "AI Content Detector": {
        "tag": "DET", "index": "03", "color": "#a78bfa", "icon": "◉",
        "desc": "Analyze submissions for AI-generated content and plagiarism signals.",
    },
    "Student Chatbot": {
        "tag": "STU", "index": "04", "color": "#f472b6", "icon": "◎",
        "desc": "A responsible, curriculum-aware assistant to support student learning.",
    },
}

# ── Helper functions (added so the app actually runs) ───────────────────────
def model_online(model_name):
    try:
        r = requests.get(OLLAMA_TAGS_URL, auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False, timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        return model_name in models
    except:
        return False

def parse_response(raw):
    segs = []
    # Extract output-text blocks
    text_matches = re.findall(r'\[output-text\](.*?)\[/output-text\]', raw, re.DOTALL)
    for match in text_matches:
        segs.append({"type": "text", "content": match.strip()})
    # Extract output-file blocks
    file_matches = re.findall(r'\[output-file-(\w+)\](.*?)\[/output-file-\1\]', raw, re.DOTALL)
    for ext, content in file_matches:
        segs.append({"type": "file", "ext": ext, "content": content.strip()})
    # Fallback if no tags
    if not segs and raw.strip():
        segs.append({"type": "text", "content": raw.strip()})
    return segs

def make_dl_bytes(content: str, ext: str):
    if ext in ["txt", "md", "py", "js", "html", "css", "json"]:
        mime = "text/plain"
    elif ext == "pdf":
        mime = "application/pdf"
    else:
        mime = "application/octet-stream"
    return io.BytesIO(content.encode("utf-8")), mime

OUT_TEXT_RE = re.compile(r'\[output-text\](.*?)\[/output-text\]', re.DOTALL)

# ── FULL CSS – Sleek blue developer theme with glassmorphism + grid background ──
st.markdown("""
<style>
/* GLOBAL */
.stApp {
  background: #020d1c !important;
  background-image: 
    linear-gradient(rgba(59,130,246,0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59,130,246,0.06) 1px, transparent 1px) !important;
  background-size: 48px 48px !important;
  color: #e2e8f0 !important;
}

/* Glassmorphism for all cards/nav */
.spartan-nav, .module-card, .chat-header, .fcard, .fgen, .file-chip {
  background: rgba(15,23,42,0.75) !important;
  backdrop-filter: blur(20px) !important;
  border: 1px solid rgba(59,130,246,0.35) !important;
  box-shadow: 0 8px 32px -6px rgba(59,130,246,0.25),
              0 0 0 1px rgba(255,255,255,0.08) inset !important;
}

/* NAV */
.spartan-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  border-bottom: 1px solid rgba(59,130,246,0.25) !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
  padding: 12px 24px !important;
  display: flex;
  align-items: center;
  gap: 16px;
}
.spartan-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 1.35rem;
  color: #3b82f6;
}
.nav-items {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.nav-item {
  background: rgba(15,23,42,0.6) !important;
  border: 1px solid rgba(59,130,246,0.3) !important;
  color: #e2e8f0 !important;
  padding: 8px 16px !important;
  border-radius: 9999px !important;
  font-size: 0.95rem;
  transition: all 0.2s;
}
.nav-item.active, .nav-item:hover {
  background: rgba(59,130,246,0.2) !important;
  border-color: #3b82f6 !important;
  color: #3b82f6 !important;
}

/* HOME */
.home-hero {
  text-align: center;
  padding: 60px 20px 40px;
}
.home-eyebrow { font-family: monospace; font-size: 0.95rem; color: #64748b; letter-spacing: 3px; }
.home-title {
  font-size: 3.2rem;
  line-height: 1.1;
  font-weight: 700;
  margin: 12px 0;
}
.home-title span { color: #3b82f6; }
.home-sub { font-size: 1.25rem; color: #94a3b8; max-width: 620px; margin: 0 auto; }

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  padding: 0 20px;
}
.module-card {
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}
.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 40px -10px rgba(59,130,246,0.4) !important;
}
.mc-tag {
  font-family: monospace;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 2px 8px;
  border-radius: 9999px;
  display: inline-block;
  margin-bottom: 12px;
}
.mc-name { font-size: 1.35rem; font-weight: 600; margin-bottom: 8px; }
.mc-desc { color: #94a3b8; line-height: 1.4; }
.mc-icon {
  position: absolute;
  bottom: 20px;
  right: 20px;
  font-size: 3rem;
  opacity: 0.15;
}

/* CHAT INPUT – centered floating glass pill */
div[data-testid="stChatInput"] {
  background: rgba(15,23,42,0.72) !important;
  backdrop-filter: blur(24px) !important;
  border: 1px solid rgba(59,130,246,0.45) !important;
  border-radius: 9999px !important;
  box-shadow: 0 10px 40px -8px rgba(59,130,246,0.35),
              0 0 0 1px rgba(255,255,255,0.1) inset !important;
  margin: 0 auto 28px auto !important;
  max-width: 780px !important;
  width: calc(100% - 40px) !important;
  position: fixed !important;
  bottom: 24px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  z-index: 9999 !important;
  padding: 6px 14px !important;
  height: 58px !important;
}
div[data-testid="stChatInput"] textarea {
  background: transparent !important;
  border: none !important;
  font-size: 1.05rem !important;
  color: #e2e8f0 !important;
  padding: 0 12px !important;
}
div[data-testid="stChatInput"] button {
  background: #3b82f6 !important;
  border-radius: 9999px !important;
  width: 42px !important;
  height: 42px !important;
  box-shadow: 0 0 18px rgba(59,130,246,0.5) !important;
}

/* Extra padding so messages aren't hidden under fixed input */
.stChatMessage { padding-bottom: 110px !important; }

/* File chip */
.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(59,130,246,0.12);
  border: 1px solid rgba(59,130,246,0.4);
  border-radius: 9999px;
  padding: 6px 14px;
  font-size: 0.82rem;
  margin-top: 8px;
  box-shadow: 0 2px 12px rgba(59,130,246,0.15);
}

/* FAB group – sits directly beside the input pill */
.fab-group {
  position: fixed !important;
  bottom: 32px !important;
  left: 50% !important;
  transform: translateX(-50%) !important;
  z-index: 10000 !important;
  display: flex !important;
  gap: 12px !important;
  width: 780px !important;
  max-width: calc(100% - 40px) !important;
  justify-content: space-between !important;
  pointer-events: none !important;
}
.fab {
  pointer-events: all !important;
  width: 48px !important;
  height: 48px !important;
  border-radius: 9999px !important;
  background: rgba(15,23,42,0.85) !important;
  border: 1px solid rgba(59,130,246,0.4) !important;
  box-shadow: 0 8px 25px rgba(59,130,246,0.3) !important;
  backdrop-filter: blur(16px) !important;
  font-size: 1.4rem !important;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fab:hover {
  transform: scale(1.08) !important;
  box-shadow: 0 0 25px rgba(59,130,246,0.6) !important;
}

/* Thinking & file generating widgets */
.thinking { display: inline-flex; align-items: center; gap: 8px; }
.fgen, .fcard { margin: 12px 0; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k,v in [("mode","Home"),("messages",[]),("pending_attach",None),
            ("attach_name",None),("attach_ext",None),("show_upload",False)]:
    if k not in st.session_state: st.session_state[k] = v

def go_tool(name):
    st.session_state.mode        = name
    st.session_state.messages    = [{"role":"assistant","content":"[output-text]System online. How can I assist you today?[/output-text]"}]
    st.session_state.pending_attach = None
    st.session_state.attach_name = None
    st.session_state.attach_ext  = None
    st.session_state.show_upload = False

def render_msg(raw, idx):
    segs = parse_response(raw)
    if not segs:
        st.markdown(raw)
        return
    for si, seg in enumerate(segs):
        if seg["type"] == "text":
            st.markdown(seg["content"])
        else:
            ext, content = seg["ext"], seg["content"]
            fname   = f"spartan-output.{ext}"
            preview = content[:300]
            kb      = round(len(content.encode())/1024,1)
            lbl     = ext.upper()
            st.markdown(f"""<div class="fcard">
<div class="fcard-hd">
  <div class="fcard-icon">{lbl}</div>
  <div><div class="fcard-name">{fname}</div><div class="fcard-meta">{kb} KB · OUTPUT READY</div></div>
</div>
<div class="fcard-preview">{preview}</div>
</div>""", unsafe_allow_html=True)
            fb, mime = make_dl_bytes(content, ext)
            st.download_button(f"↓ Download {fname}", data=fb, file_name=fname,
                               mime=mime, key=f"dl_{idx}_{si}")

# ── Top nav (ONLY navigation method) ─────────────────────────────────────────
cur_mode = st.session_state.mode
nav_items_html = ""
for name, tm in TOOL_META.items():
    active = "active" if cur_mode == name else ""
    nav_url = "?nav=" + name.replace(" ", "+")
    nav_items_html += f'<button class="nav-item {active}" onclick="window.location.href=\'{nav_url}\'">' + tm["icon"] + " " + name + "</button>"

st.markdown(f"""
<div class="spartan-nav">
  <div class="spartan-logo">
    <div class="spartan-logo-mark">S</div>
    <div>
      <div class="spartan-logo-text">Spartan AI</div>
      <div class="spartan-logo-ver">v2.0</div>
    </div>
  </div>
  <div class="nav-items">
    <button class="nav-item {'active' if cur_mode=='Home' else ''}" onclick="window.location.href='?nav=Home'">⌂ Home</button>
    {nav_items_html}
  </div>
  <div class="nav-right" style="margin-left:auto;display:flex;align-items:center;gap:8px;">
    <div class="nav-status" style="font-size:0.8rem;color:#64748b;">
      <span style="display:inline-block;width:8px;height:8px;background:#22c55e;border-radius:50%;margin-right:4px;"></span>
      System Active
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Handle nav query params ───────────────────────────────────────────────────
qp = st.query_params
if "nav" in qp:
    dest = qp["nav"].replace("+", " ")
    st.query_params.clear()
    if dest == "Home":
        st.session_state.mode = "Home"
        st.session_state.messages = []
    elif dest in MODEL_MAP:
        go_tool(dest)
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# HOME – visual cards only (no hidden buttons, no onclick – top nav is the only way)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Home":
    cards_html = ""
    for name, tm in TOOL_META.items():
        cards_html += f"""
<div class="module-card" style="color:{tm['color']};">
  <div class="mc-tag">{tm['tag']}</div>
  <div class="mc-name">{name}</div>
  <div class="mc-desc">{tm['desc']}</div>
  <div class="mc-icon">{tm['icon']}</div>
</div>"""

    st.markdown(f"""
<div class="home-hero">
  <div class="home-eyebrow">// Educational Intelligence Platform</div>
  <div class="home-title">Academic integrity,<br><span>reimagined.</span></div>
  <div class="home-sub">Four specialised AI modules for educators and students — built for speed, trust, and real learning.</div>
</div>
<div class="module-grid">{cards_html}</div>
""", unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TOOL PAGE
# ══════════════════════════════════════════════════════════════════════════════
tool  = st.session_state.mode
model = MODEL_MAP[tool]
tm    = TOOL_META[tool]
online = model_online(model)
status_cls   = "online" if online else "offline"
status_label = "Online"  if online else "Offline"

# Tool header
st.markdown(f"""
<div class="chat-header">
  <div class="ch-left">
    <div class="ch-badge" style="color:{tm['color']};border-color:{tm['color']}40;">{tm['tag']}</div>
    <div>
      <div class="ch-name">{tool}</div>
      <div class="ch-desc">{tm['desc']}</div>
    </div>
  </div>
  <div class="ch-status {status_cls}" style="font-size:0.85rem;">
    <span style="display:inline-block;width:8px;height:8px;background:#22c55e;border-radius:50%;margin-right:4px;"></span>{status_label}
  </div>
</div>
""", unsafe_allow_html=True)

# Chat history – attachment chip under user messages
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
        if msg["role"] == "assistant":
            render_msg(msg["content"], i)
        else:
            st.markdown(msg.get("display", msg["content"]))
            if msg.get("attach"):
                a = msg["attach"]
                st.markdown(f"""
                <div class="file-chip">
                  <span class="file-chip-icon">📎</span>
                  <span class="file-chip-name">{a['name']}</span>
                  <span class="file-chip-type">{a['ext'].upper()}</span>
                </div>
                """, unsafe_allow_html=True)

# Pending file chip
if st.session_state.pending_attach:
    st.markdown(f"""<div class="file-chip">
  <span class="file-chip-icon">📎</span>
  <span class="file-chip-name">{st.session_state.attach_name}</span>
  <span class="file-chip-type">{st.session_state.attach_ext.upper()}</span>
</div>""", unsafe_allow_html=True)

# Upload panel
if st.session_state.show_upload:
    up, _ = st.columns([3,1])
    with up:
        uploaded = st.file_uploader(
            "Attach a file",
            type=["pdf","docx","txt","py","js","html","css","md","json","png","jpg","jpeg","gif","bmp","tiff"],
            label_visibility="visible", key="uploader"
        )
    if uploaded and uploaded.name != st.session_state.attach_name:
        with st.spinner("Reading…"):
            raw_ext = uploaded.name.rsplit(".",1)[-1].lower()
            content = ""
            try:
                if raw_ext in ["png","jpg","jpeg","gif","bmp","tiff"]:
                    if TESSERACT_OK:
                        img = Image.open(uploaded).convert("RGB")
                        content = pytesseract.image_to_string(img, config=OCR_CONFIG).strip()
                    else:
                        content = "(OCR not available)"
                elif raw_ext == "pdf" and PyPDF2:
                    reader = PyPDF2.PdfReader(uploaded)
                    for page in reader.pages:
                        t = page.extract_text() or ""
                        content += t + "\n"
                elif raw_ext == "docx" and docx_module:
                    d = docx_module.Document(uploaded)
                    for p in d.paragraphs:
                        content += p.text + "\n"
                else:
                    content = uploaded.read().decode("utf-8", errors="ignore")
                content = content.strip() or "(empty file)"
                st.session_state.pending_attach = content
                st.session_state.attach_name    = uploaded.name
                st.session_state.attach_ext     = raw_ext
                st.session_state.show_upload    = False
                st.rerun()
            except Exception as e:
                st.error(f"Read error: {e}")

# Hidden buttons for FABs
with st.container():
    st.markdown('<div class="hidden-btns">', unsafe_allow_html=True)
    col1, col2, _ = st.columns([1,1,20])
    with col1:
        new_clicked = st.button("↺", key="btn_new")
    with col2:
        att_clicked = st.button("📎", key="btn_attach")
    st.markdown('</div>', unsafe_allow_html=True)

if new_clicked:
    go_tool(tool)
    st.rerun()
if att_clicked:
    st.session_state.show_upload = not st.session_state.show_upload
    st.rerun()

# FABs beside input
att_active = "active" if st.session_state.show_upload else ""
st.markdown(f"""
<div class="fab-group">
  <div class="fab" title="Attach file" onclick="(function(){{
    var btns=window.parent.document.querySelectorAll('button');
    for(var b of btns){{if(b.innerText.trim()==='📎'){{b.click();return;}}}}
  }})()">📎</div>
  <div class="fab" title="New chat" onclick="(function(){{
    var btns=window.parent.document.querySelectorAll('button');
    for(var b of btns){{if(b.innerText.trim()==='↺'){{b.click();return;}}}}
  }})()">↺</div>
</div>
""", unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("> message Spartan AI…")

# ── Handle send ───────────────────────────────────────────────────────────────
if user_input:
    parts = []
    attach_info = None

    if st.session_state.pending_attach:
        ext = st.session_state.attach_ext
        parts.append(f"[input-file-{ext}-text]{st.session_state.pending_attach}[/input-file-{ext}-text]")
        attach_info = {"name": st.session_state.attach_name, "ext": ext}
        st.session_state.pending_attach = None
        st.session_state.attach_name = None
        st.session_state.attach_ext = None

    parts.append(f"[input-user-text]{user_input}[/input-user-text]")
    api_content = "\n".join(parts)

    st.session_state.messages.append({
        "role": "user",
        "content": api_content,
        "display": user_input,
        "attach": attach_info
    })

    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
        if attach_info:
            st.markdown(f"""
            <div class="file-chip">
              <span class="file-chip-icon">📎</span>
              <span class="file-chip-name">{attach_info['name']}</span>
              <span class="file-chip-type">{attach_info['ext'].upper()}</span>
            </div>
            """, unsafe_allow_html=True)

    full = ""
    with st.chat_message("assistant", avatar="🤖"):
        think_slot = st.empty()
        resp_slot  = st.empty()
        think_slot.markdown("""<div class="thinking">
  <div class="tdots"><span></span><span></span><span></span></div>
  <div class="thinking-lbl">Thinking</div>
</div>""", unsafe_allow_html=True)

        FILE_GEN = """<div class="fgen"><div class="fgen-icon"><svg viewBox="0 0 16 16" fill="none"><path d="M3 2h7l4 4v9H3V2z" stroke="#06b6d4" stroke-width="1.2" stroke-linejoin="round"/><path d="M10 2v4h4" stroke="#06b6d4" stroke-width="1.2" stroke-linejoin="round"/><path d="M5 9h6M5 11.5h4" stroke="#06b6d4" stroke-width="1" stroke-linecap="round"/></svg></div><div><div class="fgen-title">Generating file…</div><div class="fgen-sub">Writing <div class="fdots"><span></span><span></span><span></span></div></div></div></div>"""

        ANY_OPEN  = re.compile(r'\[(output-text|output-file-\w+)\]')
        FILE_OPEN = re.compile(r'\[output-file-\w+\]')

        state = "waiting"
        gen_slot = None
        active = resp_slot

        try:
            payload = {
                "model": model,
                "messages": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                "stream": True,
            }
            with requests.post(OLLAMA_CHAT_URL, json=payload,
                               auth=HTTPBasicAuth(USERNAME, PASSWORD),
                               timeout=600, verify=False, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    tok = json.loads(line).get("message", {}).get("content", "")
                    full += tok

                    if state == "waiting":
                        m2 = ANY_OPEN.search(full)
                        if m2:
                            think_slot.empty()
                            if "output-file" in m2.group(1):
                                state = "file"
                                pre = OUT_TEXT_RE.sub(r'\1', full[:m2.start()]).strip()
                                if pre:
                                    active.markdown(pre)
                                gen_slot = st.empty()
                                gen_slot.markdown(FILE_GEN, unsafe_allow_html=True)
                            else:
                                state = "text"
                                live = re.sub(r'\[/output-text\].*', '', full[m2.end():]).strip()
                                if live:
                                    active.markdown(live + "▌", unsafe_allow_html=True)
                    elif state == "text":
                        m3 = re.search(r'\[output-text\](.*?)(?=\[/output-text\]|\[output-file-)', full, re.DOTALL)
                        if m3:
                            live = m3.group(1).strip()
                        else:
                            pos = full.rfind('[output-text]')
                            live = re.sub(r'\[/?$|\[/output', '', full[pos + len('[output-text]'):] if pos >= 0 else "").strip()
                        if live:
                            active.markdown(live + "▌", unsafe_allow_html=True)
                        if FILE_OPEN.search(full):
                            state = "file"
                            active.markdown(live)
                            gen_slot = st.empty()
                            gen_slot.markdown(FILE_GEN, unsafe_allow_html=True)
                    time.sleep(0.01)

            think_slot.empty()
            resp_slot.empty()
            if gen_slot:
                gen_slot.empty()
            render_msg(full, len(st.session_state.messages))

        except Exception as e:
            think_slot.empty()
            resp_slot.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(239,68,68,0.7);'>ERR // {e}</span>", unsafe_allow_html=True)

    if full:
        st.session_state.messages.append({"role": "assistant", "content": full, "display": full})
