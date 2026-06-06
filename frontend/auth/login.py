import streamlit as st
import requests
from auth.session import save_auth, is_logged_in

API_URL = "http://localhost:8000"


def show_login_page():
    """
    Full login/register UI.
    Call this from any page when user is not authenticated.
    """
    st.title("📈 PulseInvest")
    st.caption("AI-powered investment research assistant")
    st.divider()

    tab_login, tab_register = st.tabs(["Login", "Register"])

    # ── Login tab ─────────────────────────────────────────────────────────────

    with tab_login:
        st.subheader("Welcome back")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Login",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not username or not password:
                st.error("Please enter username and password")
            else:
                with st.spinner("Logging in..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/auth/login",
                            data={                       # form-encoded not JSON
                                "username": username,
                                "password": password,
                            },
                            timeout=10,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            save_auth(
                                token=data["access_token"],
                                user_id=data["user_id"],
                                username=data["username"],
                                role=data["role"],
                                session_id=data["session_id"],
                            )
                            st.success(f"Welcome back, {data['username']}!")
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Login failed"))
                    except Exception as e:
                        st.error(f"Could not connect to server: {e}")

    # ── Register tab ──────────────────────────────────────────────────────────

    with tab_register:
        st.subheader("Create account")

        with st.form("register_form"):
            reg_email    = st.text_input("Email")
            reg_username = st.text_input("Username")
            reg_password = st.text_input("Password", type="password")
            reg_confirm  = st.text_input("Confirm password", type="password")
            submitted    = st.form_submit_button(
                "Register",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not all([reg_email, reg_username, reg_password, reg_confirm]):
                st.error("All fields are required")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match")
            elif len(reg_password) < 8:
                st.error("Password must be at least 8 characters")
            else:
                with st.spinner("Creating account..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/auth/register",
                            json={
                                "email": reg_email,
                                "username": reg_username,
                                "password": reg_password,
                            },
                            timeout=10,
                        )
                        if r.status_code == 201:
                            data = r.json()
                            save_auth(
                                token=data["access_token"],
                                user_id=data["user_id"],
                                username=data["username"],
                                role=data["role"],
                                session_id=data["session_id"],
                            )
                            if data["role"] == "admin":
                                st.success("Account created! You are the first user — admin access granted.")
                            else:
                                st.success(f"Welcome, {data['username']}!")
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Registration failed"))
                    except Exception as e:
                        st.error(f"Could not connect to server: {e}")

        st.caption("First person to register gets admin access automatically.")