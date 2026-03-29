import streamlit as st

# =========================================================
# Spartan AI — Refactored SPA Version
# =========================================================

st.set_page_config(
    page_title="Spartan AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---- Example tool metadata (replace with your real tools) ----
TOOL_META = {
    "Assignment Generation": {},
    "Study Helper": {},
    "History Assistant": {},
    "Research AI": {},
    "Writing AI": {}
}

# ---- Session state ----
if "mode" not in st.session_state:
    st.session_state.mode = "Home"

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---- Tool switcher ----
def go_tool(name):
    st.session_state.mode = name

def switch_page(page):
    if st.session_state.mode != page:
        if page == "Home":
            st.session_state.mode = "Home"
            st.session_state.messages = []
        else:
            go_tool(page)

# ---- Global styling ----
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Inter, sans-serif;
}
.main .block-container{
    padding-top: 4rem;
    animation: fadeIn 0.18s ease;
}
@keyframes fadeIn{
    from{opacity:0; transform:translateY(4px);}
    to{opacity:1; transform:translateY(0);}
}
.nav-shell{
    position:fixed;
    top:0;
    left:0;
    right:0;
    height:52px;
    z-index:1000;
    backdrop-filter:blur(20px);
    -webkit-backdrop-filter:blur(20px);
    background:rgba(7,9,15,0.88);
    border-bottom:1px solid rgba(255,255,255,0.06);
}
div[data-testid="stHorizontalBlock"]{
    gap:0.35rem !important;
}
div[data-testid="stButton"] > button{
    background:transparent !important;
    border:1px solid transparent !important;
    color:#94a3b8 !important;
    font-size:0.78rem !important;
    font-weight:500 !important;
    border-radius:8px !important;
    padding:0.45rem 0.75rem !important;
    transition:all 0.15s ease !important;
    box-shadow:none !important;
}
div[data-testid="stButton"] > button:hover{
    background:rgba(255,255,255,0.05) !important;
    color:#e2e8f0 !important;
    border-color:rgba(59,130,246,0.18) !important;
}
</style>
<div class="nav-shell"></div>
""", unsafe_allow_html=True)

# ---- Navigation ----
cols = st.columns([1.4] + [1]*len(TOOL_META))

with cols[0]:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;height:40px;">
        <div style="
            width:28px;height:28px;border-radius:7px;
            background:linear-gradient(135deg,#3b82f6,#06b6d4);
            display:flex;align-items:center;justify-content:center;
            color:white;font-weight:700;
            box-shadow:0 0 12px rgba(59,130,246,0.35);
        ">S</div>
        <div>
            <div style="color:#e2e8f0;font-size:0.9rem;font-weight:600;">
                Spartan AI
            </div>
            <div style="color:#475569;font-size:0.55rem;">
                v2.0
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

pages = ["Home"] + list(TOOL_META.keys())

for i, page in enumerate(pages[1:], start=1):
    with cols[i]:
        label = page
        if st.button(label, key=f"spa_nav_{page}", use_container_width=True):
            switch_page(page)
            st.rerun()

# ---- Main page content ----
st.title(f"{st.session_state.mode}")

if st.session_state.mode == "Home":
    st.write("Welcome to Spartan AI.")
else:
    st.write(f"You are currently inside **{st.session_state.mode}**.")
