import streamlit as st
import requests
import pandas as pd
from auth.session import require_admin, get_headers

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Admin Portal", page_icon="👑", layout="wide")
require_admin()

st.title("👑 Admin Portal")

# ── Helpers ───────────────────────────────────────────────────────────────────


def api_get(path: str) -> dict | list:
    try:
        r = requests.get(f"{API_URL}{path}", headers=get_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return {}


def api_patch(path: str) -> bool:
    try:
        r = requests.patch(f"{API_URL}{path}", headers=get_headers(), timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def api_delete(path: str) -> bool:
    try:
        r = requests.delete(f"{API_URL}{path}", headers=get_headers(), timeout=10)
        return r.status_code == 200
    except Exception:
        return False


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_stats, tab_users, tab_activity = st.tabs(
    [
        "📊 Platform Stats",
        "👥 Users",
        "📋 Activity Feed",
    ]
)

# ── Platform stats ────────────────────────────────────────────────────────────

with tab_stats:
    stats = api_get("/admin/stats")

    if stats:
        st.subheader("Overview")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Users", stats.get("total_users", 0))
        col2.metric("Active Users", stats.get("active_users", 0))
        col3.metric("Total Trades", stats.get("total_trades", 0))
        col4.metric("Total Messages", stats.get("total_messages", 0))

        st.divider()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Admin Users", stats.get("admin_users", 0))
        col2.metric("Total Sessions", stats.get("total_sessions", 0))
        col3.metric("New Users Today", stats.get("new_users_today", 0))
        col4.metric("Trades Today", stats.get("new_trades_today", 0))

        st.divider()

        # inactive users
        inactive = stats.get("total_users", 0) - stats.get("active_users", 0)
        if inactive > 0:
            st.warning(f"{inactive} disabled user account(s) on the platform.")

# ── Users ─────────────────────────────────────────────────────────────────────

with tab_users:
    st.subheader("All Users")

    if st.button("🔄 Refresh", key="refresh_users"):
        st.rerun()

    users = api_get("/admin/users")

    if not users:
        st.info("No users found.")
    else:
        # summary table
        df = pd.DataFrame(
            [
                {
                    "ID": u["id"],
                    "Username": u["username"],
                    "Email": u["email"],
                    "Role": u["role"],
                    "Active": "✅" if u["is_active"] else "❌",
                    "Trades": u["total_trades"],
                    "Messages": u["total_messages"],
                    "Sessions": u["total_sessions"],
                    "Joined": str(u.get("created_at", ""))[:10],
                    "Last Login": str(u.get("last_login", "") or "Never")[:10],
                }
                for u in users
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Manage User")

        # user selector
        usernames = [u["username"] for u in users]
        selected_username = st.selectbox("Select user", usernames)
        selected = next(u for u in users if u["username"] == selected_username)

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown(f"**{selected['username']}**")
                st.caption(selected["email"])
                st.caption(f"Role: `{selected['role']}`")
                st.caption(f"Active: {'✅' if selected['is_active'] else '❌'}")
                st.caption(
                    f"Trades: {selected['total_trades']} | Messages: {selected['total_messages']}"
                )
                st.caption(f"Joined: {str(selected.get('created_at', ''))[:10]}")
                st.caption(
                    f"Last login: {str(selected.get('last_login') or 'Never')[:10]}"
                )

        with col2:
            with st.container(border=True):
                st.markdown("**Actions**")
                uid = selected["id"]

                # disable / enable
                if selected["is_active"]:
                    if st.button(
                        "🚫 Disable Account", use_container_width=True, key="disable"
                    ):
                        if api_patch(f"/admin/users/{uid}/disable"):
                            st.success(f"{selected['username']} disabled")
                            st.rerun()
                else:
                    if st.button(
                        "✅ Enable Account", use_container_width=True, key="enable"
                    ):
                        if api_patch(f"/admin/users/{uid}/enable"):
                            st.success(f"{selected['username']} enabled")
                            st.rerun()

                st.divider()

                # promote / demote
                if selected["role"] == "user":
                    if st.button(
                        "👑 Promote to Admin", use_container_width=True, key="promote"
                    ):
                        if api_patch(f"/admin/users/{uid}/promote"):
                            st.success(f"{selected['username']} promoted to admin")
                            st.rerun()
                else:
                    if st.button(
                        "⬇️ Demote to User", use_container_width=True, key="demote"
                    ):
                        if api_patch(f"/admin/users/{uid}/demote"):
                            st.success(f"{selected['username']} demoted")
                            st.rerun()

                st.divider()

                # view detail
                if st.button(
                    "🔍 View Full Detail", use_container_width=True, key="detail"
                ):
                    st.session_state.viewing_user_id = uid
                    st.rerun()

                # delete — confirmation required
                st.divider()
                with st.expander("⚠️ Danger Zone"):
                    st.warning("This permanently deletes the user and all their data.")
                    confirm = st.text_input(
                        f"Type '{selected['username']}' to confirm",
                        key="delete_confirm",
                    )
                    if st.button(
                        "🗑️ Delete User",
                        type="primary",
                        use_container_width=True,
                        key="delete",
                    ):
                        if confirm == selected["username"]:
                            if api_delete(f"/admin/users/{uid}"):
                                st.success(f"{selected['username']} deleted")
                                st.session_state.pop("viewing_user_id", None)
                                st.rerun()
                        else:
                            st.error("Username confirmation did not match")

        # ── User detail panel ──────────────────────────────────────────────

        if "viewing_user_id" in st.session_state:
            detail_id = st.session_state.viewing_user_id
            detail_user = next((u for u in users if u["id"] == detail_id), None)

            if detail_user:
                st.divider()
                st.subheader(f"Detail — {detail_user['username']}")

                detail = api_get(f"/admin/users/{detail_id}")

                if detail:
                    d_col1, d_col2 = st.columns(2)

                    with d_col1:
                        st.markdown("**Trade History**")
                        trades = detail.get("trades", [])
                        if trades:
                            df_trades = pd.DataFrame(
                                [
                                    {
                                        "Ticker": t["ticker"],
                                        "Action": t["action"],
                                        "Qty": t["quantity"],
                                        "Price": f"${t['price_at_trade']:,.4f}",
                                        "Date": str(t["created_at"])[:10],
                                    }
                                    for t in trades
                                ]
                            )
                            st.dataframe(
                                df_trades, use_container_width=True, hide_index=True
                            )
                        else:
                            st.info("No trades yet.")

                    with d_col2:
                        st.markdown("**Watchlist**")
                        watchlist = detail.get("watchlist", [])
                        if watchlist:
                            df_watch = pd.DataFrame(
                                [
                                    {
                                        "Ticker": w["ticker"],
                                        "Type": w["asset_type"],
                                        "Notes": w.get("notes") or "",
                                    }
                                    for w in watchlist
                                ]
                            )
                            st.dataframe(
                                df_watch, use_container_width=True, hide_index=True
                            )
                        else:
                            st.info("Empty watchlist.")

                    st.markdown("**Recent Chat Messages**")
                    messages = detail.get("recent_messages", [])
                    if messages:
                        for msg in messages:
                            role_icon = "🧑" if msg["role"] == "user" else "🤖"
                            with st.container(border=True):
                                st.caption(
                                    f"{role_icon} {msg['role'].upper()} · "
                                    f"{str(msg['created_at'])[:16]}"
                                )
                                st.write(msg["content"])
                                if msg.get("tools_used"):
                                    st.caption(f"🔧 {msg['tools_used']}")
                    else:
                        st.info("No messages yet.")

                if st.button("✖ Close Detail", key="close_detail"):
                    st.session_state.pop("viewing_user_id", None)
                    st.rerun()

# ── Activity feed ─────────────────────────────────────────────────────────────

with tab_activity:
    st.subheader("Recent Platform Activity")

    col1, col2 = st.columns([3, 1])
    with col2:
        limit = st.selectbox("Show", [20, 50, 100], key="activity_limit")
    with col1:
        if st.button("🔄 Refresh", key="refresh_activity"):
            st.rerun()

    activity = api_get(f"/admin/activity?limit={limit}")

    if activity:
        for item in activity:
            icon = "📈" if item["type"] == "trade" else "💬"
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"{icon} **{item['username']}** — {item['detail']}")
                with col2:
                    st.caption(str(item["created_at"])[:16])
    else:
        st.info("No activity yet.")
