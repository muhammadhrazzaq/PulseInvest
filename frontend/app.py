import streamlit as st
from auth.session import is_logged_in, is_admin, logout
from auth.login import show_login_page

st.set_page_config(
    page_title="PulseInvest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth gate ─────────────────────────────────────────────────────────────────

if not is_logged_in():
    show_login_page()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 PulseInvest")
    st.caption(f"Logged in as **{st.session_state.username}**")
    if is_admin():
        st.caption("👑 Admin")
    st.divider()

    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/01_dashboard.py", label="Dashboard", icon="📊")
    st.page_link("pages/02_research.py", label="Research", icon="🔍")
    st.page_link("pages/03_chat.py", label="Chat", icon="💬")
    st.page_link("pages/04_briefing.py", label="Morning Briefing", icon="☀️")

    if is_admin():
        st.divider()
        st.page_link("pages/05_admin.py", label="Admin Portal", icon="👑")

    st.divider()
    if st.button("Logout", use_container_width=True):
        logout()

    st.caption("⚠️ Not financial advice")

# ── Home ──────────────────────────────────────────────────────────────────────

st.title(f"Welcome, {st.session_state.username} 👋")
st.markdown("""
Your AI-powered investment research assistant.

**What you can do:**
- 📊 **Dashboard** — track your paper portfolio and watchlist
- 🔍 **Research** — deep dive into any stock or crypto
- 💬 **Chat** — ask anything about markets
- ☀️ **Morning Briefing** — daily AI summary of your watchlist

> ⚠️ PulseInvest is a research tool, not a financial advisor.
> Always do your own research before investing.
""")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.page_link(
        "pages/01_dashboard.py", label="📊 Dashboard", use_container_width=True
    )
with col2:
    st.page_link("pages/02_research.py", label="🔍 Research", use_container_width=True)
with col3:
    st.page_link("pages/03_chat.py", label="💬 Chat", use_container_width=True)
with col4:
    st.page_link("pages/04_briefing.py", label="☀️ Briefing", use_container_width=True)
