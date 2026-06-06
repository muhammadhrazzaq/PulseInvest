"""
AssetType and TradeAction enums
Same principle — constrain values so 
invalid data never reaches the database.

Trade
A single buy or sell event. The price_at_trade is 
fetched at the moment of the trade from yfinance/CoinGecko — this is 
what makes paper trading realistic. 
id is optional because it's assigned by pg on insert, not by you.

Position
A computed view of your current holding in 
one asset — calculated from all your trades 
for that ticker. pnl (profit and loss) and 
pnl_percent are derived fields, calculated 
in the service layer by comparing avg_buy_price
against current_price.

Portfolio
Aggregates all positions into a single summary.
 The four totals at the bottom are what the
 Streamlit dashboard displays as the headline numbers.

WatchlistItem
A ticker you're watching but haven't traded yet. Separate from positions.
TradeRequest
What Streamlit sends when a user clicks buy/sell.
 Notice there's no price here — 
 the backend fetches the live price itself.
This prevents the frontend from sending a stale or manipulated price.
"""






from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class AssetType(str, Enum):
    stock = "stock"
    crypto = "crypto"

class TradeAction(str, Enum):
    buy = "buy"
    sell = "sell"

class Trade(BaseModel):
    id: Optional[int] = None
    ticker: str
    asset_type: AssetType
    action: TradeAction
    quantity: float
    price_at_trade: float
    timestamp: datetime = datetime.now()
    notes: Optional[str] = None

class Position(BaseModel):
    ticker: str
    asset_type: AssetType
    quantity: float
    avg_buy_price: float
    current_price: float
    pnl: float
    pnl_percent: float

class Portfolio(BaseModel):
    positions: list[Position] = []
    total_invested: float = 0.0
    total_current_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0

class WatchlistItem(BaseModel):
    ticker: str
    asset_type: AssetType
    notes: Optional[str] = None

class TradeRequest(BaseModel):
    ticker: str
    asset_type: AssetType
    action: TradeAction
    quantity: float
    notes: Optional[str] = None