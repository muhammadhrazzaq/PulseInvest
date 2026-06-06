import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
from auth.session import require_auth, get_headers
require_auth()

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Portfolio Dashboard")

# ── Helper ────────────────────────────────────────────────────────────────────

def get_portfolio():
    try:
        r = requests.get(f"{API_URL}/portfolio/", headers=get_headers(), timeout=10)
        return r.json()
    except Exception as e:
        st.error(f"Could not fetch portfolio: {e}")
        return None

def get_watchlist():
    try:
        r = requests.get(f"{API_URL}/portfolio/watchlist", headers=get_headers(), timeout=10)
        return r.json()
    except Exception as e:
        st.error(f"Could not fetch watchlist: {e}")
        return []

def get_trades():
    try:
        r = requests.get(f"{API_URL}/portfolio/trades", headers=get_headers(), timeout=10)
        return r.json()
    except Exception as e:
        return []

# ── Portfolio summary ─────────────────────────────────────────────────────────

st.subheader("Portfolio Summary")
portfolio = get_portfolio()

if portfolio and portfolio.get("positions"):
    col1, col2, col3, col4 = st.columns(4)
    pnl_color = "normal" if portfolio["total_pnl"] >= 0 else "inverse"

    col1.metric("Total Invested", f"${portfolio['total_invested']:,.2f}")
    col2.metric("Current Value", f"${portfolio['total_current_value']:,.2f}")
    col3.metric(
        "Total P&L",
        f"${portfolio['total_pnl']:,.2f}",
        f"{portfolio['total_pnl_percent']:+.2f}%"
    )
    col4.metric(
        "Positions",
        len(portfolio["positions"])
    )

    st.divider()

    # positions table
    st.subheader("Open Positions")
    positions_data = []
    for p in portfolio["positions"]:
        positions_data.append({
            "Ticker": p["ticker"],
            "Type": p["asset_type"],
            "Quantity": p["quantity"],
            "Avg Buy": f"${p['avg_buy_price']:,.4f}",
            "Current": f"${p['current_price']:,.4f}",
            "P&L": f"${p['pnl']:,.2f}",
            "P&L %": f"{p['pnl_percent']:+.2f}%",
        })

    df = pd.DataFrame(positions_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # pie chart
    st.subheader("Allocation")
    fig = go.Figure(data=[go.Pie(
        labels=[p["ticker"] for p in portfolio["positions"]],
        values=[p["quantity"] * p["current_price"] for p in portfolio["positions"]],
        hole=0.4,
    )])
    fig.update_layout(height=350, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No positions yet. Make your first paper trade below.")

# ── Paper trading ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("Paper Trade")

with st.form("trade_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ticker = st.text_input("Ticker", placeholder="AAPL or BTC").upper()
    with col2:
        asset_type = st.selectbox("Type", ["stock", "crypto"])
    with col3:
        action = st.selectbox("Action", ["buy", "sell"])
    with col4:
        quantity = st.number_input("Quantity", min_value=0.0001, step=0.1)

    notes = st.text_input("Notes (optional)", placeholder="Why are you making this trade?")
    submitted = st.form_submit_button("Execute Trade", use_container_width=True)

    if submitted and ticker:
        try:
            r = requests.post(
                f"{API_URL}/portfolio/trade",
                json={
                    "ticker": ticker,
                    "asset_type": asset_type,
                    "action": action,
                    "quantity": quantity,
                    "notes": notes or None,
                },
                headers=get_headers(),
                timeout=15,
            )
            if r.status_code == 200:
                trade = r.json()
                st.success(
                    f"✅ {action.upper()} {quantity} {ticker} "
                    f"@ ${trade['price_at_trade']:,.4f}"
                )
                st.rerun()
            else:
                st.error(f"Trade failed: {r.json().get('detail')}")
        except Exception as e:
            st.error(f"Error: {e}")

# ── Watchlist ─────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Watchlist")

col_left, col_right = st.columns([3, 1])

with col_right:
    with st.form("watchlist_form"):
        w_ticker = st.text_input("Add ticker").upper()
        w_type = st.selectbox("Type", ["stock", "crypto"])
        w_notes = st.text_input("Notes")
        if st.form_submit_button("Add", use_container_width=True):
            if w_ticker:
                r = requests.post(
                    f"{API_URL}/portfolio/watchlist",
                    json={"ticker": w_ticker, "asset_type": w_type, "notes": w_notes or None},
                    headers=get_headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    st.success(f"Added {w_ticker}")
                    st.rerun()
                else:
                    st.error(r.json().get("detail"))

with col_left:
    watchlist = get_watchlist()
    if watchlist:
        for item in watchlist:
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            col1.write(f"**{item['ticker']}**")
            col2.write(item["asset_type"])
            price = item.get("current_price")
            col3.write(f"${price:,.4f}" if price else "N/A")
            if col4.button("❌", key=f"del_{item['ticker']}"):
                requests.delete(f"{API_URL}/portfolio/watchlist/{item['ticker']}", headers=get_headers())
                st.rerun()
    else:
        st.info("Your watchlist is empty.")

# ── Trade history ─────────────────────────────────────────────────────────────

st.divider()
with st.expander("Trade History"):
    trades = get_trades()
    if trades:
        df = pd.DataFrame([{
            "ID": t["id"],
            "Ticker": t["ticker"],
            "Type": t["asset_type"],
            "Action": t["action"],
            "Quantity": t["quantity"],
            "Price": f"${t['price_at_trade']:,.4f}",
            "Notes": t.get("notes") or "",
        } for t in trades])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No trades yet.")