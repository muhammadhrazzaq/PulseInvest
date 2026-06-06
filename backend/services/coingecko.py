import httpx
from datetime import datetime, timedelta

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# common coin id mappings so users can type BTC not "bitcoin"
COIN_ID_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
    "matic": "matic-network",
    "link": "chainlink",
    "avax": "avalanche-2",
    "uni": "uniswap",
    "ltc": "litecoin",
    "atom": "cosmos",
    "xlm": "stellar",
}

class CoinGeckoService:

    def _resolve_id(self, coin: str) -> str:
        """Convert ticker symbol to CoinGecko coin id"""
        return COIN_ID_MAP.get(coin.lower(), coin.lower())

    async def get_price(self, coin: str) -> dict:
        coin_id = self._resolve_id(coin)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{COINGECKO_BASE}/simple/price",
                    params={
                        "ids": coin_id,
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                        "include_market_cap": "true",
                        "include_24hr_vol": "true",
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                if coin_id not in data:
                    return {"error": f"Coin '{coin}' not found", "coin": coin}

                info = data[coin_id]
                return {
                    "coin": coin.upper(),
                    "coin_id": coin_id,
                    "price_usd": info.get("usd"),
                    "change_24h": info.get("usd_24h_change"),
                    "market_cap": info.get("usd_market_cap"),
                    "volume_24h": info.get("usd_24h_vol"),
                }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}", "coin": coin}
        except Exception as e:
            return {"error": str(e), "coin": coin}

    async def get_coin_info(self, coin: str) -> dict:
        coin_id = self._resolve_id(coin)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{COINGECKO_BASE}/coins/{coin_id}",
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "community_data": "false",
                        "developer_data": "false",
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                market = data.get("market_data", {})
                return {
                    "coin": coin.upper(),
                    "name": data.get("name"),
                    "symbol": data.get("symbol", "").upper(),
                    "description": data.get("description", {}).get("en", "")[:500],
                    "price_usd": market.get("current_price", {}).get("usd"),
                    "ath": market.get("ath", {}).get("usd"),
                    "ath_date": market.get("ath_date", {}).get("usd"),
                    "atl": market.get("atl", {}).get("usd"),
                    "market_cap_rank": data.get("market_cap_rank"),
                    "circulating_supply": market.get("circulating_supply"),
                    "total_supply": market.get("total_supply"),
                    "sentiment_up": data.get("sentiment_votes_up_percentage"),
                    "sentiment_down": data.get("sentiment_votes_down_percentage"),
                }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}", "coin": coin}
        except Exception as e:
            return {"error": str(e), "coin": coin}

    async def get_history(self, coin: str, days: int = 30) -> list[dict]:
        coin_id = self._resolve_id(coin)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
                    params={
                        "vs_currency": "usd",
                        "days": days,
                        "interval": "daily" if days > 7 else "hourly",
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "date": datetime.fromtimestamp(point[0] / 1000).strftime("%Y-%m-%d"),
                        "price": round(point[1], 6),
                    }
                    for point in data.get("prices", [])
                ]
        except httpx.HTTPStatusError as e:
            return [{"error": f"HTTP error: {e.response.status_code}"}]
        except Exception as e:
            return [{"error": str(e)}]

    async def get_market_overview(self) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{COINGECKO_BASE}/global",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json().get("data", {})

                return {
                    "total_market_cap_usd": data.get("total_market_cap", {}).get("usd"),
                    "total_volume_usd": data.get("total_volume", {}).get("usd"),
                    "btc_dominance": round(data.get("market_cap_percentage", {}).get("btc", 0), 2),
                    "eth_dominance": round(data.get("market_cap_percentage", {}).get("eth", 0), 2),
                    "active_coins": data.get("active_cryptocurrencies"),
                    "market_cap_change_24h": data.get("market_cap_change_percentage_24h_usd"),
                }
        except Exception as e:
            return {"error": str(e)}

    async def search_coin(self, query: str) -> list[dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{COINGECKO_BASE}/search",
                    params={"query": query},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "coin_id": c.get("id"),
                        "name": c.get("name"),
                        "symbol": c.get("symbol", "").upper(),
                        "rank": c.get("market_cap_rank"),
                    }
                    for c in data.get("coins", [])[:5]
                ]
        except Exception as e:
            return [{"error": str(e)}]

coingecko = CoinGeckoService()