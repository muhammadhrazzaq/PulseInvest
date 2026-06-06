import streamlit as st
import requests
import uuid
from auth.session import require_auth, get_headers

require_auth()

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")
st.title("💬 Chat with PulseInvest")
st.caption("Ask anything about stocks, crypto, markets, or investing concepts.")

# ── Session state ─────────────────────────────────────────────────────────────

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "tools_log" not in st.session_state:
    st.session_state.tools_log = []

# ── Sidebar controls ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Chat Controls")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        requests.delete(
            f"{API_URL}/chat/history/{st.session_state.session_id}",
            headers=get_headers(),
            timeout=5
        )
        st.session_state.chat_history = []
        st.session_state.tools_log = []
        st.rerun()

    st.divider()
    st.markdown("### Suggested prompts")
    prompts = [
        "What is the current BTC price?",
        "Research NVDA for me",
        "Give me a crypto market overview",
        "What is a P/E ratio?",
        "Compare BTC and ETH",
        "Latest news on AAPL",
        "What is dollar cost averaging?",
        "Is the market bullish or bearish today?",
    ]
    for prompt in prompts:
        if st.button(prompt, use_container_width=True, key=f"prompt_{prompt}"):
            st.session_state.pending_prompt = prompt
            st.rerun()

    st.divider()
    show_tools = st.toggle("Show tools used", value=True)
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

# ── Chat history render ───────────────────────────────────────────────────────

for i, msg in enumerate(st.session_state.chat_history):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # show tools used under assistant messages
        if (
            msg["role"] == "assistant"
            and show_tools
            and i < len(st.session_state.tools_log)
        ):
            tools = st.session_state.tools_log[i // 2]
            if tools:
                st.caption(f"🔧 Tools used: {', '.join(tools)}")

# ── Handle suggested prompt ───────────────────────────────────────────────────

if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")
    st.session_state.chat_history.append({
        "role": "user",
        "content": prompt,
    })
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                r = requests.post(
                    f"{API_URL}/chat/",
                    json={
                        "message": prompt,
                        "session_id": st.session_state.session_id,
                        "history": st.session_state.chat_history[:-1],
                    },
                    headers=get_headers(),
                    timeout=30,
                )
                result = r.json()
                reply = result.get("reply", "Sorry, something went wrong.")
                tools_used = result.get("tools_used", [])
            except Exception as e:
                reply = f"Error connecting to backend: {e}"
                tools_used = []

        st.markdown(reply)
        if show_tools and tools_used:
            st.caption(f"🔧 Tools used: {', '.join(tools_used)}")

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": reply,
    })
    st.session_state.tools_log.append(tools_used)
    st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────

if user_input := st.chat_input("Ask about any stock, crypto, or market concept..."):
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                r = requests.post(
                    f"{API_URL}/chat/",
                    json={
                        "message": user_input,
                        "session_id": st.session_state.session_id,
                        "history": st.session_state.chat_history[:-1],
                    },
                    headers=get_headers(),
                    timeout=30,
                )
                result = r.json()
                reply = result.get("reply", "Sorry, something went wrong.")
                tools_used = result.get("tools_used", [])
            except Exception as e:
                reply = f"Error connecting to backend: {e}"
                tools_used = []

        st.markdown(reply)
        if show_tools and tools_used:
            st.caption(f"🔧 Tools used: {', '.join(tools_used)}")

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": reply,
    })
    st.session_state.tools_log.append(tools_used)
    st.rerun()