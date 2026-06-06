from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db.database import get_db
from db.models import Trade, Watchlist, AssetType, TradeAction, User
from models.portfolio import (
    TradeRequest, Portfolio, Position,
    WatchlistItem, Trade as TradePydantic
)
from services.yahoo_finance import yahoo_finance
from services.coingecko import coingecko
from services.auth import get_current_user
import asyncio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def fetch_current_price(ticker: str, asset_type: str) -> float:
    if asset_type == "crypto":
        result = await coingecko.get_price(ticker)
    else:
        result = await asyncio.to_thread(yahoo_finance.get_price, ticker)

    price = result.get("price_usd") or result.get("price")
    if not price:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch price for {ticker}"
        )
    return float(price)


def calculate_portfolio(trades: list, prices: dict) -> Portfolio:
    holdings: dict[str, dict] = {}

    for trade in trades:
        key = trade.ticker
        if key not in holdings:
            holdings[key] = {
                "ticker": trade.ticker,
                "asset_type": trade.asset_type,
                "quantity": 0.0,
                "total_cost": 0.0,
            }
        if trade.action == TradeAction.buy:
            holdings[key]["quantity"] += trade.quantity
            holdings[key]["total_cost"] += trade.quantity * trade.price_at_trade
        elif trade.action == TradeAction.sell:
            holdings[key]["quantity"] -= trade.quantity
            holdings[key]["total_cost"] -= trade.quantity * trade.price_at_trade

    positions = []
    total_invested = 0.0
    total_current_value = 0.0

    for key, h in holdings.items():
        if h["quantity"] <= 0:
            continue

        current_price = prices.get(h["ticker"], 0.0)
        avg_buy_price = h["total_cost"] / h["quantity"] if h["quantity"] > 0 else 0
        current_value = h["quantity"] * current_price
        cost_basis = h["quantity"] * avg_buy_price
        pnl = current_value - cost_basis
        pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0

        positions.append(Position(
            ticker=h["ticker"],
            asset_type=h["asset_type"],
            quantity=round(h["quantity"], 6),
            avg_buy_price=round(avg_buy_price, 4),
            current_price=round(current_price, 4),
            pnl=round(pnl, 2),
            pnl_percent=round(pnl_percent, 2),
        ))

        total_invested += cost_basis
        total_current_value += current_value

    total_pnl = total_current_value - total_invested
    total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    return Portfolio(
        positions=positions,
        total_invested=round(total_invested, 2),
        total_current_value=round(total_current_value, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_percent=round(total_pnl_percent, 2),
    )


# ── Trade endpoints ───────────────────────────────────────────────────────────

@router.post("/trade", response_model=TradePydantic)
async def execute_trade(
    request: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_price = await fetch_current_price(request.ticker, request.asset_type)

    if request.action == TradeAction.sell:
        result = await db.execute(
            select(Trade).where(
                Trade.ticker == request.ticker.upper(),
                Trade.user_id == current_user.id,
            )
        )
        existing_trades = result.scalars().all()
        total_held = sum(
            t.quantity if t.action == TradeAction.buy else -t.quantity
            for t in existing_trades
        )
        if request.quantity > total_held:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot sell {request.quantity} — you only hold {round(total_held, 6)}"
            )

    trade = Trade(
        user_id=current_user.id,
        ticker=request.ticker.upper(),
        asset_type=request.asset_type,
        action=request.action,
        quantity=request.quantity,
        price_at_trade=current_price,
        notes=request.notes,
    )
    db.add(trade)
    await db.flush()
    await db.refresh(trade)

    return TradePydantic(
        id=trade.id,
        ticker=trade.ticker,
        asset_type=trade.asset_type,
        action=trade.action,
        quantity=trade.quantity,
        price_at_trade=trade.price_at_trade,
        notes=trade.notes,
    )


@router.get("/trades", response_model=list[TradePydantic])
async def get_trades(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == current_user.id)
        .order_by(Trade.created_at.desc())
    )
    trades = result.scalars().all()
    return [
        TradePydantic(
            id=t.id,
            ticker=t.ticker,
            asset_type=t.asset_type,
            action=t.action,
            quantity=t.quantity,
            price_at_trade=t.price_at_trade,
            notes=t.notes,
        )
        for t in trades
    ]


@router.delete("/trade/{trade_id}")
async def delete_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Trade).where(
            Trade.id == trade_id,
            Trade.user_id == current_user.id,
        )
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    await db.execute(
        delete(Trade).where(
            Trade.id == trade_id,
            Trade.user_id == current_user.id,
        )
    )
    return {"deleted": trade_id}


# ── Portfolio ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=Portfolio)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Trade).where(Trade.user_id == current_user.id)  # ← scoped
    )
    trades = result.scalars().all()

    if not trades:
        return Portfolio()

    holdings: dict[str, str] = {}
    for t in trades:
        holdings[t.ticker] = t.asset_type

    price_tasks = {
        ticker: fetch_current_price(ticker, asset_type)
        for ticker, asset_type in holdings.items()
    }
    prices = {}
    for ticker, task in price_tasks.items():
        try:
            prices[ticker] = await task
        except Exception:
            prices[ticker] = 0.0

    return calculate_portfolio(trades, prices)


# ── Watchlist ─────────────────────────────────────────────────────────────────

@router.post("/watchlist", response_model=WatchlistItem)
async def add_to_watchlist(
    item: WatchlistItem,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Watchlist).where(
            Watchlist.ticker == item.ticker.upper(),
            Watchlist.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"{item.ticker} already in watchlist")

    watchlist_item = Watchlist(
        user_id=current_user.id,             
        ticker=item.ticker.upper(),
        asset_type=item.asset_type,
        notes=item.notes,
    )
    db.add(watchlist_item)
    await db.flush()
    return item


@router.get("/watchlist")
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == current_user.id)  # ← scoped
    )
    items = result.scalars().all()

    if not items:
        return []

    async def enrich(item):
        try:
            price = await fetch_current_price(item.ticker, item.asset_type)
        except Exception:
            price = None
        return {
            "ticker": item.ticker,
            "asset_type": item.asset_type,
            "notes": item.notes,
            "current_price": price,
        }

    return await asyncio.gather(*[enrich(item) for item in items])


@router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.ticker == ticker.upper(),
            Watchlist.user_id == current_user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")

    await db.execute(
        delete(Watchlist).where(
            Watchlist.ticker == ticker.upper(),
            Watchlist.user_id == current_user.id,
        )
    )
    return {"removed": ticker.upper()}