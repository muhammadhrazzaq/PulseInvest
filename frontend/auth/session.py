import streamlit as st
import requests

API_URL = "http://localhost:8000"


def get_headers() -> dict:
    """Returns auth headers for API calls."""
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def is_logged_in() -> bool:
    return bool(st.session_state.get("token"))


def is_admin() -> bool:
    return st.session_state.get("role") == "admin"


def save_auth(token: str, user_id: int, username: str, role: str, session_id: str):
    """Saves auth data to session state after login/register."""
    st.session_state.token      = token
    st.session_state.user_id    = user_id
    st.session_state.username   = username
    st.session_state.role       = role
    st.session_state.session_id = session_id
    st.session_state.chat_history = []


def clear_auth():
    """Wipes all auth data from session state on logout."""
    for key in ["token", "user_id", "username", "role", "session_id", "chat_history"]:
        st.session_state.pop(key, None)


def logout():
    """Calls logout endpoint then clears local state."""
    try:
        requests.post(
            f"{API_URL}/auth/logout",
            headers=get_headers(),
            timeout=5,
        )
    except Exception:
        pass
    clear_auth()
    st.rerun()


def require_auth():
    """
    Call at top of every protected page.
    Redirects to login if not authenticated.
    """
    if not is_logged_in():
        st.warning("Please log in to access this page.")
        st.stop()


def require_admin():
    """
    Call at top of admin-only pages.
    Stops render if user is not admin.
    """
    require_auth()
    if not is_admin():
        st.error("Admin access required.")
        st.stop()