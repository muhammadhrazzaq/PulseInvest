from ddgs import DDGS
from newsapi import NewsApiClient
from db.database import settings
from datetime import datetime, timedelta


class NewsService:
    def __init__(self):
        self.newsapi = NewsApiClient(api_key=settings.news_api_key)

    def search_duckduckgo(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Real-time news search via DuckDuckGo.
        No API key, no rate limit, always fresh.
        """
        try:
            with DDGS() as ddgs:
                results = ddgs.news(
                    query,
                    max_results=max_results,
                    safesearch="moderate",
                )
                return [
                    {
                        "title": r.get("title"),
                        "summary": r.get("body"),
                        "url": r.get("url"),
                        "source": r.get("source"),
                        "published": r.get("date"),
                        "provider": "duckduckgo",
                    }
                    for r in results
                ]
        except Exception as e:
            return [{"error": str(e)}]

    def search_newsapi(self, query: str, days_back: int = 7) -> list[dict]:
        """
        Deeper research via NewsAPI.
        Free tier: articles older than 24hrs, 100 req/day.
        Good for background research on a ticker.
        """
        try:
            from_date = (datetime.today() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            response = self.newsapi.get_everything(
                q=query,
                from_param=from_date,
                language="en",
                sort_by="relevancy",
                page_size=5,
            )

            articles = response.get("articles", [])
            return [
                {
                    "title": a.get("title"),
                    "summary": a.get("description"),
                    "url": a.get("url"),
                    "source": a.get("source", {}).get("name"),
                    "published": a.get("publishedAt"),
                    "provider": "newsapi",
                }
                for a in articles
                if a.get("title") != "[Removed]"  # filter deleted articles
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def get_ticker_news(self, ticker: str, asset_type: str = "stock") -> list[dict]:
        """
        Main method called by LangChain agent.
        Combines DuckDuckGo (fresh) + NewsAPI (deeper).
        Deduplicates by title.
        """
        if asset_type == "crypto":
            query = f"{ticker} cryptocurrency news"
        else:
            query = f"{ticker} stock news"

        ddg_results = self.search_duckduckgo(query, max_results=4)
        newsapi_results = self.search_newsapi(query, days_back=7)

        combined = ddg_results + newsapi_results

        # deduplicate by title
        seen_titles = set()
        unique = []
        for article in combined:
            title = article.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique.append(article)

        return unique[:8]  # cap at 8 total

    def get_market_news(self) -> list[dict]:
        """
        General market news for morning briefing.
        No specific ticker — broad financial headlines.
        """
        try:
            results = self.search_duckduckgo(
                "stock market crypto financial news today", max_results=6
            )
            return results
        except Exception as e:
            return [{"error": str(e)}]

    def format_for_llm(self, articles: list[dict]) -> str:
        """
        Converts articles list into a clean string
        for injecting into LangChain agent context.
        """
        if not articles:
            return "No news found."

        if "error" in articles[0]:
            return f"News fetch failed: {articles[0]['error']}"

        formatted = []
        for i, a in enumerate(articles, 1):
            formatted.append(
                f"{i}. {a.get('title', 'No title')}\n"
                f"   Source: {a.get('source', 'Unknown')} | "
                f"Published: {a.get('published', 'Unknown')}\n"
                f"   {a.get('summary', 'No summary')}\n"
                f"   URL: {a.get('url', '')}"
            )

        return "\n\n".join(formatted)


news_service = NewsService()
