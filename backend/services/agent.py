import asyncio
from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from db.database import settings
from services.yahoo_finance import yahoo_finance
from services.coingecko import coingecko
from services.news import news_service
from langchain_core.messages import HumanMessage


# ── LLM ──────────────────────────────────────────────────────────────────────

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model="llama-3.3-70b-versatile",
    temperature=0.3,
)

# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_stock_price(ticker: str) -> str:
    """Get the current price, change percent, volume and market cap for a stock ticker like AAPL, NVDA, TSLA."""
    result = yahoo_finance.get_price(ticker)
    if "error" in result:
        return f"Could not fetch price for {ticker}: {result['error']}"
    return (
        f"{result['ticker']} — ${result['price']} | "
        f"Change: {round(result['change_percent'] or 0, 2)}% | "
        f"Volume: {result['volume']} | "
        f"Market Cap: ${result['market_cap']}"
    )

@tool
def get_stock_fundamentals(ticker: str) -> str:
    """Get fundamentals for a stock: PE ratio, EPS, analyst target, recommendation, business summary."""
    result = yahoo_finance.get_fundamentals(ticker)
    if "error" in result:
        return f"Could not fetch fundamentals for {ticker}: {result['error']}"
    return (
        f"{result['ticker']} ({result['name']})\n"
        f"Sector: {result['sector']} | Industry: {result['industry']}\n"
        f"P/E Ratio: {result['pe_ratio']} | EPS: {result['eps']}\n"
        f"52W High: ${result['52w_high']} | 52W Low: ${result['52w_low']}\n"
        f"Analyst Target: ${result['analyst_target']} | Recommendation: {result['recommendation']}\n"
        f"Summary: {result['summary'][:300] if result['summary'] else 'N/A'}"
    )

@tool
def get_crypto_price(coin: str) -> str:
    """Get the current price, 24h change, market cap and volume for a crypto coin like BTC, ETH, SOL."""
    result = asyncio.run(coingecko.get_price(coin))
    if "error" in result:
        return f"Could not fetch price for {coin}: {result['error']}"
    return (
        f"{result['coin']} — ${result['price_usd']} | "
        f"24h Change: {round(result['change_24h'] or 0, 2)}% | "
        f"Market Cap: ${result['market_cap']} | "
        f"24h Volume: ${result['volume_24h']}"
    )

@tool
def get_crypto_info(coin: str) -> str:
    """Get detailed info for a crypto coin: ATH, ATL, supply, market cap rank, sentiment."""
    result = asyncio.run(coingecko.get_coin_info(coin))
    if "error" in result:
        return f"Could not fetch info for {coin}: {result['error']}"
    return (
        f"{result['name']} ({result['symbol']})\n"
        f"Price: ${result['price_usd']} | Rank: #{result['market_cap_rank']}\n"
        f"ATH: ${result['ath']} on {result['ath_date']}\n"
        f"ATL: ${result['atl']}\n"
        f"Circulating Supply: {result['circulating_supply']} | Total Supply: {result['total_supply']}\n"
        f"Community Sentiment — Up: {result['sentiment_up']}% | Down: {result['sentiment_down']}%\n"
        f"About: {result['description'][:300] if result['description'] else 'N/A'}"
    )

@tool
def get_market_overview() -> str:
    """Get a global crypto market overview: total market cap, BTC dominance, ETH dominance, 24h change."""
    result = asyncio.run(coingecko.get_market_overview())
    if "error" in result:
        return f"Could not fetch market overview: {result['error']}"
    return (
        f"Global Crypto Market\n"
        f"Total Market Cap: ${result['total_market_cap_usd']:,.0f}\n"
        f"24h Volume: ${result['total_volume_usd']:,.0f}\n"
        f"BTC Dominance: {result['btc_dominance']}% | ETH Dominance: {result['eth_dominance']}%\n"
        f"Market Cap Change 24h: {round(result['market_cap_change_24h'] or 0, 2)}%\n"
        f"Active Coins: {result['active_coins']}"
    )

@tool
def get_asset_news(ticker: str, asset_type: str = "stock") -> str:
    """
    Get latest news for a stock or crypto asset.
    asset_type must be either 'stock' or 'crypto'.
    """
    articles = news_service.get_ticker_news(ticker, asset_type)
    return news_service.format_for_llm(articles)

@tool
def get_market_news() -> str:
    """Get general financial and crypto market headlines. Use for morning briefings or broad market context."""
    articles = news_service.get_market_news()
    return news_service.format_for_llm(articles)

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are PulseInvest, an AI-powered investment research assistant.

Your job is to help users make informed decisions by fetching real data and explaining it clearly.

STRICT RULES:
- Never recommend buying or selling any asset
- Never predict price movements or guarantee returns
- Always remind users you are not a financial advisor
- When a user wants to panic sell or make emotional decisions, fetch the data first and present it objectively
- If a user asks "should I buy X", explain what the data shows and let them decide

BEHAVIOURAL GUARDRAILS:
- If user mentions panic selling due to a dip, surface the historical context and their original thesis
- If user shows FOMO (fear of missing out), remind them of risk and suggest researching fundamentals first
- If user is undiversified, gently flag it

CAPABILITIES:
- Fetch live stock prices, fundamentals, analyst ratings
- Fetch live crypto prices, market cap, dominance
- Search latest news and headlines
- Give morning briefings on watchlists
- Explain financial concepts grounded in real data

Always be concise, data-driven, and neutral. End responses with a reminder that this is not financial advice when discussing specific assets."""

prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# ── Agent ─────────────────────────────────────────────────────────────────────

tools = [
    get_stock_price,
    get_stock_fundamentals,
    get_crypto_price,
    get_crypto_info,
    get_market_overview,
    get_asset_news,
    get_market_news,
]

agent = create_tool_calling_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=5,
    handle_parsing_errors=True,
    return_intermediate_steps=True,
)

# ── Run ───────────────────────────────────────────────────────────────────────

async def run_agent(message: str, chat_history: list = []) -> dict:
    # 1. Map the keys directly to match your ChatPromptTemplate structure
    result = await agent_executor.ainvoke({
        "input": message,
        "chat_history": chat_history
    })

    # 2. Extract the textual output string generated by the agent executor
    reply = result.get("output", "")

    # 3. Pull the names of the tools that were invoked from intermediate_steps
    intermediate_steps = result.get("intermediate_steps", [])
    tools_used = [action.tool for action, _ in intermediate_steps]

    return {
        "reply": reply,
        "tools_used": tools_used,
    }