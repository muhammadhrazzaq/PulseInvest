import yfinance as yf
from datetime import datetime, timedelta

class YahooFinanceService:

    def get_price(self, ticker: str) -> dict:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                "ticker": ticker.upper(),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "change_percent": info.get("regularMarketChangePercent"),
                "volume": info.get("regularMarketVolume"),
                "market_cap": info.get("marketCap"),
                "currency": info.get("currency", "USD"),
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def get_fundamentals(self, ticker: str) -> dict:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                "ticker": ticker.upper(),
                "name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "pe_ratio": info.get("trailingPE"),
                "eps": info.get("trailingEps"),
                "dividend_yield": info.get("dividendYield"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "analyst_target": info.get("targetMeanPrice"),
                "recommendation": info.get("recommendationKey"),
                "summary": info.get("longBusinessSummary"),
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def get_history(self, ticker: str, days: int = 30) -> list[dict]:
        try:
            stock = yf.Ticker(ticker)
            end = datetime.today()
            start = end - timedelta(days=days)
            hist = stock.history(start=start, end=end)

            return [
                {
                    "date": str(date.date()),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                }
                for date, row in hist.iterrows()
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def search_ticker(self, query: str) -> list[dict]:
        try:
            results = yf.Search(query)
            return [
                {
                    "ticker": r.get("symbol"),
                    "name": r.get("longname") or r.get("shortname"),
                    "type": r.get("quoteType"),
                    "exchange": r.get("exchange"),
                }
                for r in results.quotes[:5]
            ]
        except Exception as e:
            return [{"error": str(e)}]

yahoo_finance = YahooFinanceService()