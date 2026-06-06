from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models import Watchlist, Trade, AssetType
from services.yahoo_finance import yahoo_finance
from services.coingecko import coingecko
from services.news import news_service
from services.agent import run_agent
import asyncio

router = APIRouter(prefix="/briefing", tags=["briefing"])


async def fetch_price(ticker: str, asset_type: str) -> dict:
    try:
        if asset_type == AssetType.crypto:
            result = await coingecko.get_price(ticker)
            return {
                "ticker": ticker,
                "price": result.get("price_usd"),
                "change_24h": result.get("change_24h"),
                "asset_type": "crypto",
            }
        else:
            result = await asyncio.to_thread(yahoo_finance.get_price, ticker)
            return {
                "ticker": ticker,
                "price": result.get("price"),
                "change_24h": result.get("change_percent"),
                "asset_type": "stock",
            }
    except Exception:
        return {"ticker": ticker, "price": None, "change_24h": None}


@router.get("/")
async def get_morning_briefing(db: AsyncSession = Depends(get_db)):
    """
    Generates a full morning briefing:
    - Watchlist prices
    - Portfolio P&L snapshot
    - Market overview
    - Latest headlines
    - AI summary via LangChain agent
    """

    # 1. fetch watchlist
    watchlist_result = await db.execute(select(Watchlist))
    watchlist_items = watchlist_result.scalars().all()

    # 2. fetch portfolio tickers
    trades_result = await db.execute(select(Trade))
    trades = trades_result.scalars().all()
    portfolio_tickers = list({t.ticker: t.asset_type for t in trades}.items())

    # 3. combine unique tickers from both
    all_tickers = {item.ticker: item.asset_type for item in watchlist_items}
    for ticker, asset_type in portfolio_tickers:
        all_tickers[ticker] = asset_type

    # 4. fetch all prices + market news concurrently
    price_tasks = [
        fetch_price(ticker, asset_type) for ticker, asset_type in all_tickers.items()
    ]
    market_news_task = asyncio.to_thread(news_service.get_market_news)

    results = await asyncio.gather(*price_tasks, market_news_task)
    prices = results[:-1]
    market_news = results[-1]

    # 5. build context string for agent
    prices_text = "\n".join(
        [
            f"  {p['ticker']}: ${p['price']} | Change: {round(p['change_24h'] or 0, 2)}%"
            for p in prices
            if p.get("price")
        ]
    )

    news_text = news_service.format_for_llm(market_news)

    briefing_prompt = f"""
Generate a concise morning briefing for an investor.

Current prices:
{prices_text if prices_text else "No watchlist items yet."}

Market headlines:
{news_text}

Keep it under 200 words. Cover:
1. Overall market sentiment
2. Notable movers from the watchlist
3. Key news themes
4. One thing to watch today

Remind the user this is not financial advice.
"""

    # 6. run agent for AI summary
    agent_result = await run_agent(briefing_prompt)

    return {
        "prices": prices,
        "market_news": market_news[:5],
        "ai_summary": agent_result["reply"],
    }
