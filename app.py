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

# ── NEW GLOBAL STYLE: Sleek blue developer theme with glassmorphism + grid ──
st.markdown("""
<style>
/* ── GLOBAL THEME: Sleek blue developer aesthetic with glassmorphism + subtle grid ── */
.stApp {
  background: #020d1c !important;
  background-image: 
    linear-gradient(rgba(59,130,246,0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59,130,246,0.06) 1px, transparent 1px) !important;
  background-size: 48px 48px !important;
}

/* Glassmorphism base for all major UI elements */
.spartan-nav, .module-card, .chat-header, .fcard, .fgen, .file-chip {
  background: rgba(15,23,42,0.72) !important;
  backdrop-filter: blur(20px) !important;
  border: 1px solid rgba(59,130,246,0.35) !important;
  box-shadow: 0 8px 32px -6px rgba(59,130,246,0.25),
              0 0 0 1px rgba(255,255,255,0.08) inset !important;
}

/* ── NAV & HEADER ── */
.spartan-nav {
  border-bottom: 1px solid rgba(59,130,246,0.25) !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
}

/* ── CHAT INPUT BAR – FIXED, CENTERED, GLASS PILL (no big black box) ── */
div[data-testid="stChatInput"] {
  background: rgba(15,23,42,0.68) !important;
  backdrop-filter: blur(24px) !important;
  border: 1px solid rgba(59,130,246,0.45) !important;
  border-radius: 9999px !important;
  box-shadow: 
    0 10px 40px -8px rgba(59,130,246,0.35),
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

/* Make the textarea inside perfectly centered and clean */
div[data-testid="stChatInput"] textarea {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  font-size: 1.05rem !important;
  color: #e2e8f0 !important;
  padding: 0 12px !important;
  line-height: 1.4 !important;
}

/* Send button inside the pill */
div[data-testid="stChatInput"] button {
  background: #3b82f6 !important;
  border-radius: 9999px !important;
  width: 42px !important;
  height: 42px !important;
  box-shadow: 0 0 18px rgba(59,130,246,0.5) !important;
}

/* Prevent chat messages from being hidden under the fixed input */
[data-testid="stChatMessageContainer"] > div,
.stChatMessage {
  padding-bottom: 110px !important;
}

/* ── FILE CHIP (now also rendered under user messages) ── */
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

/* FABs moved to sit directly beside the centered input (left = attach, right = new) */
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
}

/* Glow on hover for that premium developer feel */
.fab:hover {
  transform: scale(1.08) !important;
  box-shadow: 0 0 25px rgba(59,130,246,0.6) !important;
}

/* All other existing classes keep their blue theme but inherit glass where possible */
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
    if not segs: st.markdown(raw); return
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

# ── Top nav injection ─────────────────────────────────────────────────────────
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
  <div class="nav-right">
    <div class="nav-status"><div class="nav-dot"></div>System Active</div>
  </div>
</div>
<div class="page-wrap"></div>
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
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Home":
    cards_html = ""
    for i,(name,tm) in enumerate(TOOL_META.items()):
        cards_html += f"""
<div class="module-card" style="color:{tm['color']};"
     onclick="window.location.href='?nav={name.replace(' ','+')}'"
     onmouseenter="this.style.borderColor='rgba(59,130,246,0.35)'"
     onmouseleave="this.style.borderColor='var(--bdr)'">
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

    # Hidden Streamlit buttons for module cards (click target)
    c = st.columns(4)
    for i, name in enumerate(TOOL_META):
        with c[i]:
            if st.button(name, key=f"home_{name}"):
                go_tool(name)
                st.rerun()
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
  <div class="ch-status {status_cls}">
    <div class="ch-status-dot"></div>{status_label}
  </div>
</div>
""", unsafe_allow_html=True)

# Chat history (UPDATED: attachment chip now appears UNDER user messages)
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="🤖" if msg["role"]=="assistant" else "👤"):
        if msg["role"] == "assistant":
            render_msg(msg["content"], i)
        else:
            st.markdown(msg.get("display", msg["content"]))
            # Show attached file directly under the user message
            if msg.get("attach"):
                a = msg["attach"]
                st.markdown(f"""
                <div class="file-chip">
                  <span class="file-chip-icon">📎</span>
                  <span class="file-chip-name">{a['name']}</span>
                  <span class="file-chip-type">{a['ext'].upper()}</span>
                </div>
                """, unsafe_allow_html=True)

# File chip if pending (before send)
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
                # Image → OCR
                if raw_ext in ["png","jpg","jpeg","gif","bmp","tiff"]:
                    if TESSERACT_OK:
                        img = Image.open(uploaded).convert("RGB")
                        content = pytesseract.image_to_string(img, config=OCR_CONFIG).strip()
                    else:
                        content = "(pytesseract not installed — cannot OCR image)"
                # PDF
                elif raw_ext == "pdf":
                    if PyPDF2:
                        reader = PyPDF2.PdfReader(uploaded)
                        for page in reader.pages:
                            t = page.extract_text()
                            if t: content += t + "\n"
                    else:
                        content = "(PyPDF2 not installed)"
                # DOCX
                elif raw_ext == "docx":
                    if docx_module:
                        d = docx_module.Document(uploaded)
                        for p in d.paragraphs: content += p.text + "\n"
                    else:
                        content = "(python-docx not installed)"
                # All text-based formats
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

# Hidden action buttons (triggered by FAB JS)
with st.container():
    st.markdown('<div class="hidden-btns">', unsafe_allow_html=True)
    _col1, _col2, _ = st.columns([1,1,20])
    with _col1:
        new_clicked = st.button("↺", key="btn_new")
    with _col2:
        att_clicked = st.button("📎", key="btn_attach")
    st.markdown('</div>', unsafe_allow_html=True)

if new_clicked:
    go_tool(tool); st.rerun()
if att_clicked:
    st.session_state.show_upload = not st.session_state.show_upload; st.rerun()

# FAB overlay (now positioned beside the centered input)
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

# ── Handle send (UPDATED: store attach info so it renders under the user message) ──
if user_input:
    parts = []
    attach_info = None

    if st.session_state.pending_attach:
        ext = st.session_state.attach_ext
        parts.append(f"[input-file-{ext}-text]{st.session_state.pending_attach}[/input-file-{ext}-text]")
        attach_info = {
            "name": st.session_state.attach_name,
            "ext": ext
        }
        # Clear pending immediately
        st.session_state.pending_attach = None
        st.session_state.attach_name = None
        st.session_state.attach_ext = None

    parts.append(f"[input-user-text]{user_input}[/input-user-text]")
    api_content = "\n".join(parts)

    # Store attach metadata with the message
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

        # Tag-aware streaming state machine
        ANY_OPEN  = re.compile(r'\[(output-text|output-file-\w+)\]')
        FILE_OPEN = re.compile(r'\[output-file-\w+\]')

        state = "waiting"; gen_slot = None; active = resp_slot
        try:
            payload = {
                "model": model,
                "messages": [{"role":m["role"],"content":m["content"]} for m in st.session_state.messages],
                "stream": True,
            }
            with requests.post(OLLAMA_CHAT_URL, json=payload,
                               auth=HTTPBasicAuth(USERNAME,PASSWORD),
                               timeout=600, verify=False, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line: continue
                    tok = json.loads(line).get("message",{}).get("content","")
                    full += tok

                    if state == "waiting":
                        m2 = ANY_OPEN.search(full)
                        if m2:
                            think_slot.empty()
                            if "output-file" in m2.group(1):
                                state = "file"
                                pre = OUT_TEXT_RE.sub(r'\1', full[:m2.start()]).strip()
                                if pre: active.markdown(pre)
                                gen_slot = st.empty()
                                gen_slot.markdown(FILE_GEN, unsafe_allow_html=True)
                            else:
                                state = "text"
                                live = re.sub(r'\[/output-text\].*','', full[m2.end():]).strip()
                                if live: active.markdown(live+"▌", unsafe_allow_html=True)
                    elif state == "text":
                        m3 = re.search(r'\[output-text\](.*?)(?=\[/output-text\]|\[output-file-)', full, re.DOTALL)
                        if m3:
                            live = m3.group(1).strip()
                        else:
                            pos = full.rfind('[output-text]')
                            live = re.sub(r'\[/?$|\[/output','', full[pos+len('[output-text]'):]).strip() if pos>=0 else ""
                        if live: active.markdown(live+"▌", unsafe_allow_html=True)
                        if FILE_OPEN.search(full):
                            state="file"; active.markdown(live)
                            gen_slot = st.empty()
                            gen_slot.markdown(FILE_GEN, unsafe_allow_html=True)
                    time.sleep(0.01)

            think_slot.empty(); resp_slot.empty()
            if gen_slot: gen_slot.empty()
            render_msg(full, len(st.session_state.messages))

        except Exception as e:
            think_slot.empty()
            resp_slot.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(239,68,68,0.7);'>ERR // {e}</span>", unsafe_allow_html=True)

    if full:
        st.session_state.messages.append({"role":"assistant","content":full,"display":full})
