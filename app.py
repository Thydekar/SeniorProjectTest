import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json
import time
import pytesseract
from PIL import Image
import io

# =============================
# CONFIG — ONLY CHANGE THESE
# =============================
NGROK_URL = "https://ona-overcritical-extrinsically.ngrok-free.dev"

MODEL_ASSIGNMENT_GEN = "gemma3"
MODEL_GRADER         = "spartan-grader"
MODEL_PLAGIARISM     = "spartan-detector"
MODEL_STUDENT_CHAT   = "spartan-student"

OLLAMA_CHAT_URL = f"{NGROK_URL}/api/chat"
USERNAME = "dgeurts"
PASSWORD = "thaidakar21"
OCR_CONFIG = r"--oem 3 --psm 6"

st.set_page_config(page_title="Spartan AI Demo", layout="centered")

# =============================
# MODERN DARK THEME + FIXED BAR
# =============================
st.markdown("""
<style>
    body {background:#0d1117;}
    .main {background:#0d1117 !important; color:#c9d1d9;}
    section[data-testid="stSidebar"] {background:#161b22;}
    h1,h2 {color:#58a6ff;}

    /* FIXED bottom chat container */
    .chat-container {
        position: fixed;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        background: #0d1117;
        border-top: 1px solid #30363d;
        padding: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 99999;
    }

    /* Custom image upload button */
    .upload-btn {
        background: #238636;
        border: none;
        color: white;
        font-size: 22px;
        padding: 8px 14px;
        border-radius: 10px;
        cursor: pointer;
        height: 42px;
    }
    .upload-btn:hover {background:#2ea043;}

    /* Fully hide the Streamlit uploader */
    div[data-testid="stFileUploader"] {
        opacity: 0 !important;
        height: 0px !important;
        width: 0px !important;
        overflow: hidden !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    .footer {
        text-align:center; 
        color:#8b949e;
        font-size:0.85em; 
        margin-top:60px; 
        padding-bottom:160px;
    }
</style>
""", unsafe_allow_html=True)


# =============================
# STATE
# =============================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role":"assistant","content":"Hello! How can I help you today?"}]

if "pending_image" not in st.session_state:
    st.session_state.pending_image = None


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.title("Spartan AI Demo")

    if st.button("Home", key="home"):
        for k in ["mode","messages","pending_image", "hidden_upload"]:
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown("**Tools**")
    for label,key in [
        ("Assignment Generation","a"),
        ("Assignment Grader","g"),
        ("AI Content/Plagiarism Detector","d"),
        ("Student Chatbot","s")
    ]:
        if st.button(label,key=key):
            st.session_state.mode = label
            st.session_state.messages = [
                {"role":"assistant","content":"Hello! How can I help you today?"}
            ]
            st.session_state.pending_image = None
            st.session_state.hidden_upload = None
            st.rerun()
    st.markdown("---")
    st.caption("Senior Project • Dallin Geurts")


# =============================
# MODE HANDLING
# =============================
mode = st.session_state.get("mode","Home")
model_map = {
    "Assignment Generation": MODEL_ASSIGNMENT_GEN,
    "Assignment Grader": MODEL_GRADER,
    "AI Content/Plagiarism Detector": MODEL_PLAGIARISM,
    "Student Chatbot": MODEL_STUDENT_CHAT
}

if mode == "Home":
    st.title("Spartan AI Demo")
    st.markdown("### Empowering Education with Responsible AI")
    st.markdown("A modern AI assistant for schools.")
    st.markdown("<div class='footer'>Spartan AI • Senior Project • 2025</div>", unsafe_allow_html=True)
    st.stop()

current_model = model_map[mode]
st.title(mode)


# =============================
# CHAT DISPLAY
# =============================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("display_text", msg.get("content", "")))
        if msg.get("image"):
            st.image(msg["image"], width=300)

# Spacer above fixed bar
st.markdown("<div style='height:160px;'></div>", unsafe_allow_html=True)


# =============================
# FIXED BOTTOM BAR
# =============================
st.markdown("""
<div class="chat-container">
    <button class="upload-btn" id="open-file">
        📷
    </button>
""", unsafe_allow_html=True)

# Hidden file uploader (triggered by JS)
hidden_uploader = st.file_uploader(
    "Upload image",
    type=["png","jpg","jpeg"],
    key="hidden_upload",
    label_visibility="collapsed"
)

# JS to trigger hidden uploader
st.markdown("""
<script>
document.getElementById('open-file').onclick = function() {
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) fileInput.click();
}
</script>
""", unsafe_allow_html=True)

# Chat input
prompt = st.chat_input("Type your message...")
st.markdown("</div>", unsafe_allow_html=True)  # end bar


# =============================
# IMAGE HANDLING
# =============================
if hidden_uploader is not None:
    with st.spinner("Reading image..."):
        try:
            img = Image.open(hidden_uploader).convert("RGB")
            big = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
            ocr = pytesseract.image_to_string(big, config=OCR_CONFIG).strip()

            thumb = img.copy()
            thumb.thumbnail((300, 300))
            buf = io.BytesIO()
            thumb.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            st.session_state.pending_image = {
                "thumb": img_bytes,
                "ocr": ocr
            }

            st.success("Image ready!")

        except:
            st.error("Failed to read image.")
            st.session_state.pending_image = None


# =============================
# SEND USER MESSAGE
# =============================
if prompt:
    image_data = None
    ai_text = ""

    if st.session_state.pending_image:
        if st.session_state.pending_image["ocr"].strip():
            ai_text += f"uploaded-image-text{{{st.session_state.pending_image['ocr']}}}\n"
        image_data = st.session_state.pending_image["thumb"]

    ai_text += f"user-query{{{prompt}}}"

    # Append user message
    st.session_state.messages.append({
        "role": "user",
        "content": ai_text,
        "display_text": prompt,
        "image": image_data
    })

    with st.chat_message("user"):
        st.markdown(prompt)
        if image_data:
            st.image(image_data, width=300)

    # Clear image so it doesn't attach again
    st.session_state.pending_image = None
    st.session_state.hidden_upload = None

    # ============================
    # AI RESPONSE
    # ============================
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""

        try:
            payload = {
                "model": current_model,
                "messages": st.session_state.messages[:-1]
                           + [{"role": "user", "content": ai_text}],
                "stream": True
            }

            with requests.post(
                OLLAMA_CHAT_URL,
                json=payload,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                timeout=600,
                verify=False,
                stream=True
            ) as r:
                r.raise_for_status()

                for line in r.iter_lines():
                    if line:
                        token = json.loads(line).get("message", {}).get("content", "")
                        full += token
                        placeholder.markdown(full + "▍")

                placeholder.markdown(full)

        except:
            full = "Connection failed."
            placeholder.error(full)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full,
            "display_text": full
        })


# =============================
# FOOTER
# =============================
st.markdown("<div class='footer'>Spartan AI • Senior Project • 2025</div>", unsafe_allow_html=True)
