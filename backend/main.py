from fastapi import FastAPI
from contextlib import asynccontextmanager
from db.database import engine, Base
from db import models  # noqa
from api.chat import router as chat_router
from api.portfolio import router as portfolio_router
from api.market import router as market_router
from api.briefing import router as briefing_router
from api.auth import router as auth_router
from api.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables ready")
    yield
    await engine.dispose()
    print("Shutting down...")

app = FastAPI(
    title="PulseInvest API",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(chat_router)
app.include_router(portfolio_router)
app.include_router(market_router)
app.include_router(briefing_router)
app.include_router(auth_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {"status": "ok"}