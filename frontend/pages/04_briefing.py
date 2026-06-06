import streamlit as st
import requests
import plotly.express as px
import pandas as pd
from datetime import datetime
from auth.session import require_auth, get_headers

require_auth()

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Morning Briefing", page_icon="☀️", layout="wide")
st.title("☀️ Morning Briefing")

now = datetime.now()
st.caption(f"{now.strftime('%A, %d %B %Y')} · {now.strftime('%H:%M')}")

# ── Generate briefing ─────────────────────────────────────────────────────────

col1, col2 = st.columns([3, 1])
with col2:
    generate = st.button(
        "Generate Briefing",
        use_container_width=True,
        type="primary"
    )

with col1:
    st.write("Get your daily AI-powered market summary based on your watchlist and portfolio.")

if "briefing" not in st.session_state:
    st.session_state.briefing = None

if generate:
    with st.spinner("Fetching market data and generating your briefing..."):
        try:
            r = requests.get(f"{API_URL}/briefing/", headers=get_headers(), timeout=45)
            if r.status_code == 200:
                st.session_state.briefing = r.json()
            else:
                st.error(f"Failed to generate briefing: {r.text}")
        except Exception as e:
            st.error(f"Error: {e}")

# ── Render briefing ───────────────────────────────────────────────────────────

briefing = st.session_state.briefing

if briefing:

    # ── AI summary ────────────────────────────────────────────────────────────

    st.divider()
    st.subheader("📝 AI Summary")

    with st.container(border=True):
        st.markdown(briefing.get("ai_summary", "No summary available."))
        st.caption("⚠️ This is not financial advice. Always do your own research.")

    st.divider()

    # ── Price snapshot ────────────────────────────────────────────────────────

    prices = briefing.get("prices", [])

    if prices:
        st.subheader("📊 Price Snapshot")

        valid_prices = [p for p in prices if p.get("price")]

        if valid_prices:
            cols = st.columns(min(len(valid_prices), 4))
            for i, item in enumerate(valid_prices):
                col = cols[i % 4]
                change = item.get("change_24h") or 0
                col.metric(
                    label=f"{item['ticker']} ({item['asset_type']})",
                    value=f"${item['price']:,.4f}",
                    delta=f"{change:+.2f}%",
                )

        st.divider()

        # price change bar chart
        df_prices = pd.DataFrame([
            {
                "Ticker": p["ticker"],
                "Change %": round(p.get("change_24h") or 0, 2),
                "Direction": "▲" if (p.get("change_24h") or 0) >= 0 else "▼",
            }
            for p in valid_prices
        ])

        if not df_prices.empty:
            fig = px.bar(
                df_prices,
                x="Ticker",
                y="Change %",
                color="Change %",
                color_continuous_scale=["#ef4444", "#f97316", "#22c55e"],
                color_continuous_midpoint=0,
                title="24h Price Change (%)",
                text="Change %",
            )
            fig.update_traces(texttemplate="%{text:+.2f}%", textposition="outside")
            fig.update_layout(
                height=350,
                margin=dict(t=40, b=0, l=0, r=0),
                coloraxis_showscale=False,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Market news ───────────────────────────────────────────────────────────

    st.divider()
    st.subheader("📰 Market Headlines")

    news = briefing.get("market_news", [])

    if news:
        for article in news:
            if "error" in article:
                continue
            with st.container(border=True):
                col_text, col_link = st.columns([5, 1])
                with col_text:
                    st.markdown(f"**{article.get('title', 'No title')}**")
                    st.caption(
                        f"{article.get('source', 'Unknown')} · "
                        f"{str(article.get('published', ''))[:10]} · "
                        f"via {article.get('provider', '')}"
                    )
                    summary = article.get("summary")
                    if summary:
                        st.write(summary[:200] + "..." if len(summary) > 200 else summary)
                with col_link:
                    url = article.get("url")
                    if url:
                        st.link_button("Read →", url)
    else:
        st.info("No market news available.")

    # ── Refresh footer ────────────────────────────────────────────────────────

    st.divider()
    col1, col2 = st.columns([3, 1])
    col1.caption(f"Last generated: {now.strftime('%H:%M:%S')}")
    if col2.button("🔄 Refresh", use_container_width=True):
        st.session_state.briefing = None
        st.rerun()

else:
    # ── Empty state ───────────────────────────────────────────────────────────

    st.divider()
    with st.container(border=True):
        st.markdown("""
        ### How to get the most from your briefing

        1. **Add assets to your watchlist** on the Dashboard page
        2. **Make some paper trades** to build a portfolio
        3. **Click Generate Briefing** above

        The briefing will cover:
        - Live prices for all your watchlist and portfolio assets
        - 24h price changes visualised as a bar chart
        - Latest market headlines from DuckDuckGo
        - AI summary with key themes and movers
        """)