from fastapi import APIRouter, Query
from services.yahoo_finance import yahoo_finance
from services.coingecko import coingecko
from services.news import news_service
import asyncio

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/stock/{ticker}")
async def get_stock(ticker: str):
    """Full stock research — price, fundamentals, history, news in one call."""
    price, fundamentals, history, news = await asyncio.gather(
        asyncio.to_thread(yahoo_finance.get_price, ticker),
        asyncio.to_thread(yahoo_finance.get_fundamentals, ticker),
        asyncio.to_thread(yahoo_finance.get_history, ticker, 30),
        asyncio.to_thread(news_service.get_ticker_news, ticker, "stock"),
    )
    return {
        "ticker": ticker.upper(),
        "price": price,
        "fundamentals": fundamentals,
        "history": history,
        "news": news,
    }


@router.get("/stock/{ticker}/history")
async def get_stock_history(
    ticker: str,
    days: int = Query(default=30, ge=7, le=365)
):
    """Stock price history for charting. days param: 7, 30, 90, 180, 365."""
    history = await asyncio.to_thread(yahoo_finance.get_history, ticker, days)
    return {"ticker": ticker.upper(), "days": days, "history": history}


@router.get("/stock/search/{query}")
async def search_stock(query: str):
    """Search for a stock ticker by company name."""
    results = await asyncio.to_thread(yahoo_finance.search_ticker, query)
    return {"query": query, "results": results}


@router.get("/crypto/{coin}")
async def get_crypto(coin: str):
    """Full crypto research — price, info, history, news in one call."""
    price, info, history, news = await asyncio.gather(
        coingecko.get_price(coin),
        coingecko.get_coin_info(coin),
        coingecko.get_history(coin, 30),
        asyncio.to_thread(news_service.get_ticker_news, coin, "crypto"),
    )
    return {
        "coin": coin.upper(),
        "price": price,
        "info": info,
        "history": history,
        "news": news,
    }


@router.get("/crypto/{coin}/history")
async def get_crypto_history(
    coin: str,
    days: int = Query(default=30, ge=7, le=365)
):
    """Crypto price history for charting."""
    history = await coingecko.get_history(coin, days)
    return {"coin": coin.upper(), "days": days, "history": history}


@router.get("/crypto/search/{query}")
async def search_crypto(query: str):
    """Search for a crypto coin by name."""
    results = await coingecko.search_coin(query)
    return {"query": query, "results": results}


@router.get("/overview")
async def get_market_overview():
    """Global crypto market overview + general market news."""
    overview, news = await asyncio.gather(
        coingecko.get_market_overview(),
        asyncio.to_thread(news_service.get_market_news),
    )
    return {
        "crypto_overview": overview,
        "market_news": news,
    }