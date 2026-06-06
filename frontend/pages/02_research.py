import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from auth.session import require_auth, get_headers

require_auth()

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Research", page_icon="🔍", layout="wide")
st.title("🔍 Research")

# ── Asset selector ────────────────────────────────────────────────────────────

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    ticker = (
        st.text_input(
            "Enter ticker or coin",
            placeholder="AAPL, NVDA, BTC, ETH...",
        )
        .upper()
        .strip()
    )

with col2:
    asset_type = st.selectbox("Asset type", ["stock", "crypto"])

with col3:
    days = st.selectbox("History", [7, 30, 90, 180, 365], index=1)

search = st.button("Research", use_container_width=True, type="primary")

# ── Fetch + render ────────────────────────────────────────────────────────────

if search and ticker:
    endpoint = (
        f"{API_URL}/market/{'stock' if asset_type == 'stock' else 'crypto'}/{ticker}"
    )

    with st.spinner(f"Fetching data for {ticker}..."):
        try:
            r = requests.get(endpoint, headers=get_headers(), timeout=20)
            data = r.json()
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            st.stop()

    if "error" in data.get("price", {}):
        st.error(f"Could not find {ticker}. Check the ticker and try again.")
        st.stop()

    # ── Price header ──────────────────────────────────────────────────────────

    price_data = data.get("price", {})
    info_data = data.get("fundamentals") or data.get("info", {})

    name = info_data.get("name") or info_data.get("longName") or ticker
    price = price_data.get("price") or price_data.get("price_usd")
    change = price_data.get("change_percent") or price_data.get("change_24h") or 0

    st.subheader(f"{name} ({ticker})")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Price",
        f"${price:,.4f}" if price else "N/A",
        f"{change:+.2f}%" if change else None,
    )

    if asset_type == "stock":
        col2.metric("P/E Ratio", info_data.get("pe_ratio") or "N/A")
        col3.metric("EPS", info_data.get("eps") or "N/A")
        col4.metric("Analyst Target", f"${info_data.get('analyst_target') or 'N/A'}")
    else:
        col2.metric("Market Cap Rank", f"#{info_data.get('market_cap_rank') or 'N/A'}")
        col3.metric(
            "ATH", f"${info_data.get('ath'):,.2f}" if info_data.get("ath") else "N/A"
        )
        col4.metric("Sentiment 👍", f"{info_data.get('sentiment_up') or 0:.1f}%")

    st.divider()

    # ── Chart + fundamentals side by side ─────────────────────────────────────

    chart_col, info_col = st.columns([3, 2])

    with chart_col:
        history = data.get("history", [])
        if history and "error" not in history[0]:
            df = pd.DataFrame(history)
            df["date"] = pd.to_datetime(df["date"])

            if asset_type == "stock" and "open" in df.columns:
                # candlestick for stocks
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=df["date"],
                            open=df["open"],
                            high=df["high"],
                            low=df["low"],
                            close=df["close"],
                            name=ticker,
                        )
                    ]
                )
            else:
                # line chart for crypto
                fig = px.line(
                    df,
                    x="date",
                    y="price",
                    title=f"{ticker} — {days}d Price",
                )

            fig.update_layout(
                height=400,
                margin=dict(t=30, b=0, l=0, r=0),
                xaxis_rangeslider_visible=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No chart data available.")

    with info_col:
        st.markdown("#### Fundamentals")

        if asset_type == "stock":
            fields = {
                "Sector": info_data.get("sector"),
                "Industry": info_data.get("industry"),
                "52W High": f"${info_data.get('52w_high'):,.2f}"
                if info_data.get("52w_high")
                else None,
                "52W Low": f"${info_data.get('52w_low'):,.2f}"
                if info_data.get("52w_low")
                else None,
                "Dividend Yield": f"{info_data.get('dividend_yield') or 0:.2%}",
                "Recommendation": info_data.get("recommendation", "").upper(),
            }
        else:
            fields = {
                "Symbol": info_data.get("symbol"),
                "ATH Date": info_data.get("ath_date", "")[:10]
                if info_data.get("ath_date")
                else None,
                "ATL": f"${info_data.get('atl'):,.4f}"
                if info_data.get("atl")
                else None,
                "Circulating Supply": f"{info_data.get('circulating_supply'):,.0f}"
                if info_data.get("circulating_supply")
                else None,
                "Total Supply": f"{info_data.get('total_supply'):,.0f}"
                if info_data.get("total_supply")
                else None,
                "Sentiment 👎": f"{info_data.get('sentiment_down') or 0:.1f}%",
            }

        for label, value in fields.items():
            if value:
                col_l, col_r = st.columns(2)
                col_l.caption(label)
                col_r.write(value)

        # business summary / description
        summary = info_data.get("summary") or info_data.get("description")
        if summary:
            st.divider()
            st.caption("About")
            st.write(summary[:400] + "..." if len(summary) > 400 else summary)

    st.divider()

    # ── News ──────────────────────────────────────────────────────────────────

    st.subheader("Latest News")
    news = data.get("news", [])

    if news and "error" not in news[0]:
        for article in news[:6]:
            with st.container():
                col_text, col_link = st.columns([5, 1])
                with col_text:
                    st.markdown(f"**{article.get('title', 'No title')}**")
                    st.caption(
                        f"{article.get('source', '')} · "
                        f"{article.get('published', '')[:10]} · "
                        f"via {article.get('provider', '')}"
                    )
                    if article.get("summary"):
                        st.write(article["summary"][:200] + "...")
                with col_link:
                    if article.get("url"):
                        st.link_button("Read →", article["url"])
                st.divider()
    else:
        st.info("No news found for this asset.")

    # ── Add to watchlist shortcut ─────────────────────────────────────────────

    st.divider()
    col1, col2 = st.columns([3, 1])
    col1.write(f"Want to track {ticker}?")
    if col2.button("Add to Watchlist", use_container_width=True):
        r = requests.post(
            f"{API_URL}/portfolio/watchlist",
            json={"ticker": ticker, "asset_type": asset_type},
            headers=get_headers(),
            timeout=10,
        )
        if r.status_code == 200:
            st.success(f"✅ {ticker} added to watchlist")
        else:
            st.warning(r.json().get("detail", "Already in watchlist"))
