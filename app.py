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

# ── Helper functions ───────────────────────────────────────────────────────────
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
    text_matches = re.findall(r'\[output-text\](.*?)\[/output-text\]', raw, re.DOTALL)
    for match in text_matches:
        segs.append({"type": "text", "content": match.strip()})
    file_matches = re.findall(r'\[output-file-(\w+)\](.*?)\[/output-file-\1\]', raw, re.DOTALL)
    for ext, content in file_matches:
        segs.append({"type": "file", "ext": ext, "content": content.strip()})
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

# ── ORIGINAL CSS + GRID BACKGROUND (exactly what you asked for) ───────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
:root {
  --bg: #07090f;
  --bg1: #0d1117;
  --bg2: #111827;
  --bg3: #1a2235;
  --blue: #3b82f6;
  --blue-d: #1d4ed8;
  --blue-lo: rgba(59,130,246,0.08);
  --blue-bd: rgba(59,130,246,0.25);
  --cyan: #06b6d4;
  --cyan-lo: rgba(6,182,212,0.08);
  --cyan-bd: rgba(6,182,212,0.25);
  --green: #10b981;
  --red: #ef4444;
  --txt: #e2e8f0;
  --txt2: #94a3b8;
  --txt3: #475569;
  --bdr: rgba(255,255,255,0.06);
  --bdr2: rgba(59,130,246,0.18);
  --radius: 10px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"],.stApp{
  background:var(--bg)!important;
  font-family:'Inter',sans-serif!important;
  color:var(--txt)!important;
  -webkit-font-smoothing:antialiased!important;
}
/* GRID BACKGROUND + original radial glow */
.stApp{
  background:
    linear-gradient(rgba(59,130,246,0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59,130,246,0.06) 1px, transparent 1px),
    radial-gradient(ellipse 60% 40% at 50% -10%,rgba(59,130,246,0.06) 0%,transparent 60%),
    var(--bg)!important;
  background-size: 48px 48px, 48px 48px, auto, auto !important;
}
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(59,130,246,0.3);border-radius:4px;}
#MainMenu,footer,header,
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton{display:none!important;}
/* ── HIDE SIDEBAR ── */
section[data-testid="stSidebar"]{display:none!important;}
.stAppHeader{display:none!important;}
/* ── APP SHELL ── */
.stApp > div[data-testid="stAppViewContainer"]{
  padding-top:0!important;
}
.main .block-container{
  max-width:100%!important;
  padding:0!important;
}
/* ── TOP NAV ── */
.spartan-nav{
  position:fixed;top:0;left:0;right:0;
  height:52px;
  background:rgba(7,9,15,0.92);
  backdrop-filter:blur(20px);
  -webkit-backdrop-filter:blur(20px);
  border-bottom:1px solid var(--bdr);
  display:flex;align-items:center;
  padding:0 24px;
  z-index:1000;
  gap:0;
}
.spartan-logo{
  display:flex;align-items:center;gap:10px;
  margin-right:32px;flex-shrink:0;
}
.spartan-logo-mark{
  width:28px;height:28px;border-radius:7px;
  background:linear-gradient(135deg,var(--blue),var(--cyan));
  display:flex;align-items:center;justify-content:center;
  font-family:'JetBrains Mono',monospace;font-size:0.7rem;font-weight:700;
  color:#fff;
  box-shadow:0 0 12px rgba(59,130,246,0.35);
}
.spartan-logo-text{
  font-size:0.9rem;font-weight:600;color:var(--txt);letter-spacing:-0.01em;
}
.spartan-logo-ver{
  font-family:'JetBrains Mono',monospace;font-size:0.5rem;
  color:var(--txt3);letter-spacing:0.1em;margin-top:1px;
}
.nav-items{display:flex;align-items:center;gap:2px;flex:1;}
.nav-item{
  padding:6px 12px;border-radius:6px;
  font-size:0.78rem;font-weight:500;color:var(--txt2);
  cursor:pointer;transition:all 0.15s;white-space:nowrap;
  border:1px solid transparent;
  font-family:'Inter',sans-serif;
  background:none;
}
.nav-item:hover{color:var(--txt);background:rgba(255,255,255,0.05);}
.nav-item.active{
  color:var(--blue);
  background:rgba(59,130,246,0.1);
  border-color:var(--blue-bd);
}
.nav-right{
  display:flex;align-items:center;gap:8px;margin-left:auto;flex-shrink:0;
}
.nav-status{
  display:flex;align-items:center;gap:6px;
  font-family:'JetBrains Mono',monospace;font-size:0.55rem;
  color:var(--txt3);letter-spacing:0.1em;text-transform:uppercase;
  padding:4px 10px;border-radius:20px;
  border:1px solid var(--bdr);
}
.nav-dot{
  width:5px;height:5px;border-radius:50%;
  background:var(--green);box-shadow:0 0 6px var(--green);
  animation:pulse 2.5s ease-in-out infinite;
}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.3;}}
/* ── PAGE WRAPPER ── */
.page-wrap{
  padding-top:52px;
  min-height:100vh;
}
/* ── HOME PAGE ── */
.home-hero{
  max-width:800px;margin:0 auto;
  padding:80px 32px 48px;
  text-align:center;
}
.home-eyebrow{
  font-family:'JetBrains Mono',monospace;font-size:0.6rem;
  letter-spacing:0.3em;text-transform:uppercase;color:var(--blue);
  opacity:0.8;margin-bottom:20px;
}
.home-title{
  font-size:clamp(2.2rem,5vw,3.4rem);font-weight:700;
  line-height:1.1;letter-spacing:-0.03em;color:var(--txt);
  margin-bottom:18px;
}
.home-title span{
  background:linear-gradient(135deg,var(--blue),var(--cyan));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.home-sub{
  font-size:1rem;color:var(--txt2);line-height:1.7;
  max-width:480px;margin:0 auto 56px;font-weight:300;
}
.module-grid{
  display:grid;grid-template-columns:repeat(2,1fr);gap:12px;
  max-width:800px;margin:0 auto;padding:0 32px 80px;
}
.module-card{
  background:var(--bg1);border:1px solid var(--bdr);border-radius:var(--radius);
  padding:24px;cursor:pointer;transition:all 0.2s;
  position:relative;overflow:hidden;text-align:left;
}
.module-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,currentColor,transparent);opacity:0;
  transition:opacity 0.2s;
}
.module-card:hover{
  background:var(--bg2);border-color:var(--blue-bd);
  transform:translateY(-2px);box-shadow:0 8px 32px rgba(0,0,0,0.3);
}
.module-card:hover::before{opacity:1;}
.mc-tag{
  display:inline-flex;align-items:center;gap:5px;
  font-family:'JetBrains Mono',monospace;font-size:0.55rem;
  font-weight:700;letter-spacing:0.12em;
  padding:3px 8px;border-radius:4px;border:1px solid currentColor;
  margin-bottom:14px;opacity:0.75;
}
.mc-tag::before{content:'';width:4px;height:4px;border-radius:50%;background:currentColor;}
.mc-name{font-size:1rem;font-weight:600;color:var(--txt);margin-bottom:8px;letter-spacing:-0.01em;}
.mc-desc{font-size:0.78rem;color:var(--txt2);line-height:1.6;font-weight:300;}
.mc-icon{position:absolute;right:18px;bottom:14px;font-size:2rem;opacity:0.04;color:currentColor;}
/* ── TOOL LAYOUT ── */
.tool-layout{
  display:flex;height:calc(100vh - 52px);
}
/* ── CHAT PANEL ── */
.chat-panel{
  flex:1;display:flex;flex-direction:column;
  overflow:hidden;
}
.chat-header{
  padding:20px 32px 16px;
  border-bottom:1px solid var(--bdr);
  background:rgba(7,9,15,0.8);
  backdrop-filter:blur(10px);
  flex-shrink:0;
  display:flex;align-items:center;justify-content:space-between;
}
.ch-left{display:flex;align-items:center;gap:14px;}
.ch-badge{
  font-family:'JetBrains Mono',monospace;font-size:0.55rem;font-weight:700;
  letter-spacing:0.1em;padding:4px 9px;border-radius:4px;
  border:1px solid currentColor;opacity:0.8;flex-shrink:0;
}
.ch-name{font-size:1rem;font-weight:600;color:var(--txt);letter-spacing:-0.015em;}
.ch-desc{font-size:0.73rem;color:var(--txt3);margin-top:2px;}
.ch-status{
  display:flex;align-items:center;gap:6px;
  font-family:'JetBrains Mono',monospace;font-size:0.52rem;
  letter-spacing:0.12em;text-transform:uppercase;flex-shrink:0;
}
.ch-status.online{color:var(--green);}
.ch-status.offline{color:var(--red);}
.ch-status-dot{width:5px;height:5px;border-radius:50%;}
.ch-status.online .ch-status-dot{background:var(--green);box-shadow:0 0 5px var(--green);animation:pulse 2.5s ease-in-out infinite;}
.ch-status.offline .ch-status-dot{background:var(--red);box-shadow:0 0 4px rgba(239,68,68,0.4);}
/* ── MESSAGES ── */
.chat-messages{
  flex:1;overflow-y:auto;
  padding:24px 32px;
  display:flex;flex-direction:column;gap:16px;
  padding-bottom:100px;
}
.stChatMessage{background:transparent!important;border:none!important;padding:4px 0!important;}
div[data-testid="chatAvatarIcon-assistant"]{
  width:28px!important;height:28px!important;
  border-radius:7px!important;overflow:hidden!important;flex-shrink:0!important;
  border:1px solid rgba(59,130,246,0.3)!important;
  background-size:cover!important;background-position:center!important;
  background-repeat:no-repeat!important;
}
div[data-testid="chatAvatarIcon-assistant"] > *{display:none!important;}
div[data-testid="chatAvatarIcon-user"]{
  width:28px!important;height:28px!important;
  border-radius:7px!important;overflow:hidden!important;flex-shrink:0!important;
  border:1px solid rgba(239,68,68,0.3)!important;
  background-size:cover!important;background-position:center!important;
  background-repeat:no-repeat!important;
}
div[data-testid="chatAvatarIcon-user"] > *{display:none!important;}
div[data-testid="stChatMessageUser"]{flex-direction:row-reverse!important;}
div[data-testid="stChatMessageUser"] > div[data-testid="stChatMessageContent"]{
  background:rgba(59,130,246,0.07)!important;
  border:1px solid rgba(59,130,246,0.18)!important;
  border-radius:12px 3px 12px 12px!important;
  padding:11px 15px!important;max-width:72%!important;
  font-size:0.87rem!important;line-height:1.7!important;
  box-shadow:none!important;
}
div[data-testid="stChatMessageAssistant"] > div[data-testid="stChatMessageContent"]{
  background:var(--bg1)!important;
  border:1px solid var(--bdr)!important;
  border-left:2px solid var(--cyan)!important;
  border-radius:3px 12px 12px 12px!important;
  padding:12px 16px!important;max-width:88%!important;
  font-size:0.87rem!important;line-height:1.75!important;
  box-shadow:none!important;
}
/* ── BOTTOM INPUT ZONE ── */
div[data-testid="stBottom"]{
  position:fixed!important;
  bottom:0!important;left:0!important;right:0!important;
  z-index:500!important;
  background:linear-gradient(to top,#07090f 55%,transparent)!important;
  padding:8px 32px 16px 32px!important;
  pointer-events:none!important;
}
div[data-testid="stBottom"] > div{
  max-width:900px!important;margin:0 auto!important;
  pointer-events:all!important;
}
div[data-testid="stChatInput"]{
  background:var(--bg1)!important;
  border:1px solid var(--bdr2)!important;
  border-radius:12px!important;
  box-shadow:0 0 0 1px rgba(59,130,246,0.05),0 8px 32px rgba(0,0,0,0.4)!important;
}
div[data-testid="stChatInput"]:focus-within{
  border-color:rgba(59,130,246,0.45)!important;
  box-shadow:0 0 0 3px rgba(59,130,246,0.07),0 8px 32px rgba(0,0,0,0.4)!important;
}
div[data-testid="stChatInput"] textarea{
  background:transparent!important;color:var(--txt)!important;
  font-family:'Inter',sans-serif!important;font-size:0.87rem!important;
  caret-color:var(--blue)!important;
}
div[data-testid="stChatInput"] textarea::placeholder{
  color:var(--txt3)!important;font-size:0.82rem!important;
}
div[data-testid="stChatInput"] button{
  background:var(--blue)!important;border:none!important;
  border-radius:7px!important;width:28px!important;height:28px!important;
  box-shadow:0 0 12px rgba(59,130,246,0.3)!important;
  flex-shrink:0!important;margin:auto 6px auto 0!important;padding:0!important;
}
div[data-testid="stChatInput"] button svg path,
div[data-testid="stChatInput"] button svg rect{fill:#fff!important;}

/* ── FLOATING ACTION BUTTONS (centered left=attach, right=new) ── */
.fab-group{
  position:fixed;bottom:32px;left:50%;transform:translateX(-50%);
  z-index:600;
  display:flex;gap:12px;
  width:780px;max-width:calc(100% - 40px);
  justify-content:space-between;
  pointer-events:none;
}
.fab{
  pointer-events:all;
  width:48px;height:48px;
  display:flex;align-items:center;justify-content:center;
  background:var(--bg2);
  border:1px solid var(--bdr2);border-radius:9999px;
  font-size:1.4rem;color:var(--txt2);
  cursor:pointer;transition:all 0.15s;
  backdrop-filter:blur(12px);
  box-shadow:0 8px 25px rgba(59,130,246,0.3);
  user-select:none;
}
.fab:hover{
  background:rgba(59,130,246,0.12);
  border-color:var(--blue-bd);color:var(--blue);
  box-shadow:0 4px 16px rgba(59,130,246,0.15);
  transform:scale(1.08);
}
.fab.active{
  background:rgba(59,130,246,0.15);
  border-color:var(--blue);color:var(--blue);
}

/* ── FILE ATTACH CHIP ── */
.file-chip{
  display:inline-flex;align-items:center;gap:8px;
  background:rgba(59,130,246,0.06);border:1px solid var(--blue-bd);
  border-radius:8px;padding:7px 12px;margin-bottom:12px;
  font-size:0.78rem;
}
.file-chip-icon{font-size:0.85rem;}
.file-chip-name{color:var(--txt);font-weight:500;}
.file-chip-type{
  font-family:'JetBrains Mono',monospace;font-size:0.6rem;
  color:var(--blue);letter-spacing:0.08em;text-transform:uppercase;
}
/* ── FILE DOWNLOAD CARD ── */
.fcard{
  background:var(--bg2);border:1px solid var(--bdr2);
  border-left:2px solid var(--blue);border-radius:10px;
  padding:16px 18px;margin:6px 0;
}
.fcard-hd{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
.fcard-icon{
  width:32px;height:32px;border-radius:6px;
  background:rgba(59,130,246,0.08);border:1px solid var(--blue-bd);
  display:flex;align-items:center;justify-content:center;
  font-family:'JetBrains Mono',monospace;font-size:0.55rem;font-weight:700;color:var(--blue);
  flex-shrink:0;
}
.fcard-name{font-size:0.82rem;font-weight:600;color:var(--txt);}
.fcard-meta{font-family:'JetBrains Mono',monospace;font-size:0.5rem;color:var(--txt3);margin-top:2px;}
.fcard-preview{
  background:rgba(0,0,0,0.3);border:1px solid var(--bdr);border-radius:6px;
  padding:8px 12px;margin-bottom:10px;
  font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:var(--txt2);
  line-height:1.55;white-space:pre-wrap;word-break:break-word;
  max-height:80px;overflow:hidden;position:relative;
}
.fcard-preview::after{
  content:'';position:absolute;bottom:0;left:0;right:0;height:24px;
  background:linear-gradient(transparent,rgba(0,0,0,0.8));
}
/* ── FILE GENERATING WIDGET ── */
.fgen{
  background:var(--bg2);border:1px solid rgba(6,182,212,0.25);
  border-left:2px solid var(--cyan);border-radius:10px;
  padding:14px 16px;display:flex;align-items:center;gap:12px;margin:6px 0;
}
.fgen-icon{
  width:32px;height:32px;border-radius:6px;flex-shrink:0;
  background:rgba(6,182,212,0.08);border:1px solid rgba(6,182,212,0.25);
  display:flex;align-items:center;justify-content:center;
}
.fgen-icon svg{width:14px;height:14px;}
.fgen-title{font-size:0.8rem;font-weight:600;color:var(--txt);margin-bottom:4px;}
.fgen-sub{
  font-family:'JetBrains Mono',monospace;font-size:0.5rem;
  color:var(--cyan);letter-spacing:0.08em;
  display:flex;align-items:center;gap:6px;
}
.fdots{display:flex;gap:3px;}
.fdots span{
  display:block;width:3px;height:3px;border-radius:50%;background:var(--cyan);
  animation:blink 1.1s ease-in-out infinite both;
}
.fdots span:nth-child(2){animation-delay:0.2s;}
.fdots span:nth-child(3){animation-delay:0.4s;}
@keyframes blink{0%,80%,100%{opacity:0.1;transform:scale(0.6);}40%{opacity:1;transform:scale(1);}}
/* ── THINKING ── */
.thinking{display:inline-flex;align-items:center;gap:8px;padding:4px 0;}
.tdots{display:flex;gap:4px;}
.tdots span{
  display:block;width:5px;height:5px;border-radius:50%;
  background:var(--blue);box-shadow:0 0 5px rgba(59,130,246,0.4);
  animation:blink 1.1s ease-in-out infinite both;
}
.tdots span:nth-child(2){animation-delay:0.2s;}
.tdots span:nth-child(3){animation-delay:0.4s;}
.thinking-lbl{
  font-family:'JetBrains Mono',monospace;font-size:0.5rem;
  color:var(--txt3);letter-spacing:0.2em;text-transform:uppercase;
}
/* ── UPLOADER ── */
div[data-testid="stFileUploader"]>div{
  background:rgba(13,17,23,0.8)!important;
  border:1px dashed var(--bdr2)!important;border-radius:8px!important;padding:12px!important;
}
div[data-testid="stFileUploader"]>div:hover{background:var(--blue-lo)!important;border-color:rgba(59,130,246,0.4)!important;}
div[data-testid="stFileUploader"] label,
div[data-testid="stFileUploader"] small{
  font-family:'JetBrains Mono',monospace!important;color:var(--txt2)!important;font-size:0.6rem!important;
}
/* ── HIDDEN ACTION BUTTONS ── */
.hidden-btns{
  position:absolute;left:-9999px;top:-9999px;
  opacity:0;pointer-events:none;width:0;height:0;overflow:hidden;
}
/* ── ALERTS ── */
div[data-testid="stAlert"]{
  background:var(--blue-lo)!important;border:1px solid var(--blue-bd)!important;
  border-radius:8px!important;font-family:'JetBrains Mono',monospace!important;font-size:0.68rem!important;
}
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

# ── Hidden nav trigger buttons — Streamlit handles state; JS (below) hides them ─
_nav_cols = st.columns(len(TOOL_META) + 1)
with _nav_cols[0]:
    if st.button("nav:Home", key="navbtn_Home"):
        st.session_state.mode = "Home"
        st.session_state.messages = []
        st.rerun()
for _i, _name in enumerate(TOOL_META.keys(), start=1):
    with _nav_cols[_i]:
        if st.button("nav:" + _name, key="navbtn_" + _name):
            go_tool(_name)
            st.rerun()

# JS: collapse every column that holds a trigger button (runs after React renders)
_HIDE_JS = (
    '<script>'
    '(function(){'
    'var L=["nav:Home","nav:Assignment Generation","nav:Assignment Grader",'
    '"nav:AI Content Detector","nav:Student Chatbot","\u21ba","\U0001F4CE"];'
    'function h(){'
    'window.parent.document.querySelectorAll("button").forEach(function(b){'
    'if(L.indexOf(b.innerText.trim())!==-1){'
    'var c=b.closest(\'[data-testid="column"]\');'
    'if(c)c.style.display="none";'
    '}});}'
    'h();setTimeout(h,200);setTimeout(h,600);'
    '})();'
    '</script>'
)
st.markdown(_HIDE_JS, unsafe_allow_html=True)

# ── Top nav (HTML shell — JS above clicks the hidden Streamlit buttons) ────────
cur_mode = st.session_state.mode

def _nav_js(label):
    return (
        "(function(){"
        "var btns=window.parent.document.querySelectorAll('button');"
        "for(var b of btns){if(b.innerText.trim()==='" + label + "'){b.click();return;}}"
        "})()"
    )

nav_items_html = ""
for name, tm in TOOL_META.items():
    active = "active" if cur_mode == name else ""
    js = _nav_js("nav:" + name)
    nav_items_html += (
        '<button class="nav-item ' + active + '" onclick="' + js + '">'
        + tm["icon"] + " " + name + "</button>"
    )

home_active = "active" if cur_mode == "Home" else ""
home_js = _nav_js("nav:Home")

st.markdown(
    '<div class="spartan-nav">'
    '<div class="spartan-logo">'
    '<div class="spartan-logo-mark">S</div>'
    '<div><div class="spartan-logo-text">Spartan AI</div>'
    '<div class="spartan-logo-ver">v2.0</div></div>'
    '</div>'
    '<div class="nav-items">'
    '<button class="nav-item ' + home_active + '" onclick="' + home_js + '">&#8962; Home</button>'
    + nav_items_html +
    '</div>'
    '<div class="nav-right"><div class="nav-status">'
    '<div class="nav-dot"></div>System Active'
    '</div></div>'
    '</div>',
    unsafe_allow_html=True
)

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "Home":
    cards_html = ""
    for name, tm in TOOL_META.items():
        card_js = _nav_js("nav:" + name)
        cards_html += (
            '<div class="module-card" style="color:' + tm['color'] + ';" onclick="' + card_js + '">'
            '<div class="mc-tag">' + tm['tag'] + '</div>'
            '<div class="mc-name">' + name + '</div>'
            '<div class="mc-desc">' + tm['desc'] + '</div>'
            '<div class="mc-icon">' + tm['icon'] + '</div>'
            '</div>'
        )

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
if tool not in MODEL_MAP:
    st.session_state.mode = "Home"
    st.rerun()
model = MODEL_MAP[tool]
tm    = TOOL_META[tool]
online = model_online(model)
status_cls   = "online" if online else "offline"
status_label = "Online"  if online else "Offline"

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

# Chat history
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

# Hidden FAB triggers
with st.container():
    col1, col2, _ = st.columns([1,1,20])
    with col1:
        new_clicked = st.button("↺", key="btn_new")
    with col2:
        att_clicked = st.button("📎", key="btn_attach")

if new_clicked:
    go_tool(tool)
    st.rerun()
if att_clicked:
    st.session_state.show_upload = not st.session_state.show_upload
    st.rerun()

# FABs (centered beside input)
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
                    if not line: continue
                    tok = json.loads(line).get("message", {}).get("content", "")
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
                                live = re.sub(r'\[/output-text\].*', '', full[m2.end():]).strip()
                                if live: active.markdown(live + "▌", unsafe_allow_html=True)
                    elif state == "text":
                        m3 = re.search(r'\[output-text\](.*?)(?=\[/output-text\]|\[output-file-)', full, re.DOTALL)
                        if m3:
                            live = m3.group(1).strip()
                        else:
                            pos = full.rfind('[output-text]')
                            live = re.sub(r'\[/?$|\[/output', '', full[pos + len('[output-text]'):] if pos >= 0 else "").strip()
                        if live: active.markdown(live + "▌", unsafe_allow_html=True)
                        if FILE_OPEN.search(full):
                            state = "file"
                            active.markdown(live)
                            gen_slot = st.empty()
                            gen_slot.markdown(FILE_GEN, unsafe_allow_html=True)
                    time.sleep(0.01)

            think_slot.empty()
            resp_slot.empty()
            if gen_slot: gen_slot.empty()
            render_msg(full, len(st.session_state.messages))

        except Exception as e:
            think_slot.empty()
            resp_slot.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(239,68,68,0.7);'>ERR // {e}</span>", unsafe_allow_html=True)

    if full:
        st.session_state.messages.append({"role": "assistant", "content": full, "display": full})
