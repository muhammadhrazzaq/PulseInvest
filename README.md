# PulseInvest 📈
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)
![LangChain](https://img.shields.io/badge/LangChain-latest-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Stars](https://img.shields.io/github/stars/yourname/PulseInvest?style=social)

AI-powered investment research assistant built with FastAPI, Streamlit, LangChain, and Groq.

>  PulseInvest is a research and education tool. It is not financial advice. Never invest based solely on AI output.

---

## What it does

- **Research** any stock or crypto — live prices, fundamentals, charts, analyst ratings
- **Chat** with an AI agent that fetches real data to answer your questions
- **Paper trade** — practice buying and selling at live prices with no real money
- **Morning briefing** — daily AI summary of your watchlist and market headlines
- **Multi-user** — each user has their own portfolio, watchlist, and chat history
- **Admin portal** — manage users, view activity, platform stats

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.11+ |
| Frontend | Streamlit |
| AI | LangChain + Groq (llama3-groq-70b-8192-tool-use-preview) |
| Database | PostgreSQL + SQLAlchemy (async) |
| Migrations | Alembic |
| Stock data | yfinance (free, no key) |
| Crypto data | CoinGecko API (free, no key) |
| News | DuckDuckGo + NewsAPI |
| Auth | JWT (python-jose) + bcrypt |
| Package manager | uv |
| Containerisation | Docker + docker-compose |

---

## Project structure

```
PulseInvest/
│
├── backend/
│   ├── main.py                        # FastAPI entry point
│   ├── pyproject.toml                 # uv dependencies
│   ├── .env                           # secrets (never commit)
│   │
│   ├── api/
│   │   ├── auth.py                    # register, login, logout
│   │   ├── chat.py                    # chat endpoint + session management
│   │   ├── portfolio.py               # paper trading + watchlist
│   │   ├── market.py                  # stock + crypto research endpoints
│   │   ├── briefing.py                # morning briefing endpoint
│   │   └── admin.py                   # admin-only endpoints
│   │
│   ├── services/
│   │   ├── agent.py                   # LangChain agent + tools
│   │   ├── auth.py                    # JWT + password hashing + dependencies
│   │   ├── yahoo_finance.py           # yfinance wrapper
│   │   ├── coingecko.py               # CoinGecko API wrapper
│   │   ├── news.py                    # DuckDuckGo + NewsAPI wrapper
│   │   └── chains/
│   │       ├── briefing.py            # morning briefing chain
│   │       ├── research.py            # asset research chain
│   │       └── guardrails.py          # behavioural guardrail chain
│   │
│   ├── models/
│   │   ├── chat.py                    # Pydantic schemas — chat
│   │   └── portfolio.py               # Pydantic schemas — trades, portfolio
│   │
│   └── db/
│       ├── database.py                # async engine + session + settings
│       ├── models.py                  # SQLAlchemy table definitions
│       └── migrations/                # Alembic migrations
│           └── versions/
│
├── frontend/
│   ├── app.py                         # Streamlit entry point + auth gate
│   ├── pyproject.toml
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── session.py                 # JWT session state helpers
│   │   └── login.py                   # login + register UI
│   │
│   └── pages/
│       ├── 01_dashboard.py            # portfolio + paper trading + watchlist
│       ├── 02_research.py             # asset research + charts + news
│       ├── 03_chat.py                 # AI chat interface
│       ├── 04_briefing.py             # morning briefing
│       └── 05_admin.py                # admin portal
│
├── docker-compose.yml
└── README.md
```

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourname/PulseInvest.git
cd PulseInvest
```

### 2. Start Postgres and pgAdmin

```bash
docker-compose up db pgadmin -d
```

pgAdmin is available at `http://localhost:5050`
- Email: `admin@pulse.com`
- Password: `admin`

Connect to DB inside pgAdmin:
- Host: `db`
- Port: `5432`
- Username: `pulse`
- Password: `pulse`
- Database: `pulse_invest`

### 3. Configure backend

```bash
cd backend
cp .env.example .env
```

Edit `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://pulse:pulse@localhost:5432/pulse_invest
GROQ_API_KEY=
NEWS_API_KEY=
SECRET_KEY=
```

Get your free API keys:
- **Groq** → [console.groq.com](https://console.groq.com) — free, no credit card
- **NewsAPI** → [newsapi.org](https://newsapi.org) — free tier, 100 req/day
- **Secret key** → run `python -c "import secrets; print(secrets.token_hex(32))"`

### 4. Install backend dependencies

```bash
cd backend
uv sync
```

### 5. Run database migrations

```bash
cd backend
uv run alembic upgrade head
```

### 6. Start the backend

```bash
cd backend
uv run uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

### 7. Install frontend dependencies

```bash
cd frontend
uv sync
```

### 8. Start the frontend

```bash
cd frontend
uv run streamlit run app.py
```

Frontend runs at `http://localhost:8501`

---

## First run

1. Open `http://localhost:8501`
2. Click **Register**
3. The first user to register is automatically made **admin**
4. All subsequent registrations are regular users

---

## API endpoints

### Auth
```
POST   /auth/register
POST   /auth/login
GET    /auth/me
POST   /auth/logout
POST   /auth/change-password
```

### Chat
```
POST   /chat/
GET    /chat/history/{session_id}
GET    /chat/sessions
DELETE /chat/history/{session_id}
```

### Portfolio
```
GET    /portfolio/
POST   /portfolio/trade
GET    /portfolio/trades
DELETE /portfolio/trade/{trade_id}
POST   /portfolio/watchlist
GET    /portfolio/watchlist
DELETE /portfolio/watchlist/{ticker}
```

### Market
```
GET    /market/stock/{ticker}
GET    /market/stock/{ticker}/history
GET    /market/stock/search/{query}
GET    /market/crypto/{coin}
GET    /market/crypto/{coin}/history
GET    /market/crypto/search/{query}
GET    /market/overview
```

### Briefing
```
GET    /briefing/
```

### Admin
```
GET    /admin/stats
GET    /admin/users
GET    /admin/users/{id}
PATCH  /admin/users/{id}/disable
PATCH  /admin/users/{id}/enable
PATCH  /admin/users/{id}/promote
PATCH  /admin/users/{id}/demote
DELETE /admin/users/{id}
GET    /admin/activity
```

---

## Docker — run everything together

```bash
docker-compose up
```

This starts Postgres, pgAdmin, backend, and frontend in the correct order.

Access:
- Frontend → `http://localhost:8501`
- Backend docs → `http://localhost:8000/docs`
- pgAdmin → `http://localhost:5050`

---

## Development workflow

```bash
# add a backend dependency
cd backend && uv add httpx

# add a frontend dependency
cd frontend && uv add plotly

# create a new migration after changing db/models.py
cd backend && uv run alembic revision --autogenerate -m "describe change"

# apply migrations
cd backend && uv run alembic upgrade head

# roll back last migration
cd backend && uv run alembic downgrade -1
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Postgres connection string |
| `GROQ_API_KEY` | ✅ | Groq API key for LLM |
| `NEWS_API_KEY` | ✅ | NewsAPI key for news search |
| `SECRET_KEY` | ✅ | JWT signing secret |

---

## Data sources

| Source | Data | Cost |
|---|---|---|
| yfinance | Stock prices, fundamentals, history | Free, no key |
| CoinGecko | Crypto prices, market data, history | Free, no key |
| DuckDuckGo | Real-time news headlines | Free, no key |
| NewsAPI | Archived news articles | Free tier (100/day) |

---

## Disclaimer

PulseInvest is built for learning and research purposes only.

- It does not provide financial advice
- It does not recommend buying or selling any asset
- It cannot predict price movements
- Past data shown in the app does not guarantee future results

Always consult a qualified financial advisor before making investment decisions.

---

## License

MIT
