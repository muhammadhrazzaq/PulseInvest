from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from db.database import get_db
from db.models import User, UserRole, Session as DBSession, ChatMessage, Trade, Watchlist
from services.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


class UserSummary(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None
    total_trades: int
    total_messages: int
    total_sessions: int


class UserDetail(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None
    trades: list[dict]
    watchlist: list[dict]
    recent_messages: list[dict]


class PlatformStats(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_trades: int
    total_messages: int
    total_sessions: int
    new_users_today: int
    new_trades_today: int


@router.get("/stats", response_model=PlatformStats)
async def get_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide stats for admin dashboard."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # counts
    total_users     = await db.execute(select(func.count(User.id)))
    active_users    = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    admin_users     = await db.execute(select(func.count(User.id)).where(User.role == UserRole.admin))
    total_trades    = await db.execute(select(func.count(Trade.id)))
    total_messages  = await db.execute(select(func.count(ChatMessage.id)))
    total_sessions  = await db.execute(select(func.count(DBSession.id)))
    new_users_today = await db.execute(select(func.count(User.id)).where(User.created_at >= today))
    new_trades_today = await db.execute(select(func.count(Trade.id)).where(Trade.created_at >= today))

    return PlatformStats(
        total_users=total_users.scalar() or 0,
        active_users=active_users.scalar() or 0,
        admin_users=admin_users.scalar() or 0,
        total_trades=total_trades.scalar() or 0,
        total_messages=total_messages.scalar() or 0,
        total_sessions=total_sessions.scalar() or 0,
        new_users_today=new_users_today.scalar() or 0,
        new_trades_today=new_trades_today.scalar() or 0,
    )



@router.get("/users", response_model=list[UserSummary])
async def get_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with activity summary."""
    result = await db.execute(
        select(User).order_by(desc(User.created_at))
    )
    users = result.scalars().all()

    summaries = []
    for user in users:

        trades_count = await db.execute(
            select(func.count(Trade.id)).where(Trade.user_id == user.id)
        )
        messages_count = await db.execute(
            select(func.count(ChatMessage.id))
            .join(DBSession, ChatMessage.session_id == DBSession.id)
            .where(DBSession.user_id == user.id)
        )
        sessions_count = await db.execute(
            select(func.count(DBSession.id)).where(DBSession.user_id == user.id)
        )

        summaries.append(UserSummary(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            total_trades=trades_count.scalar() or 0,
            total_messages=messages_count.scalar() or 0,
            total_sessions=sessions_count.scalar() or 0,
        ))

    return summaries



@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user_detail(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Full detail for a specific user — trades, watchlist, recent chat."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # trades
    trades_result = await db.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(desc(Trade.created_at))
        .limit(50)
    )
    trades = [
        {
            "id": t.id,
            "ticker": t.ticker,
            "asset_type": t.asset_type,
            "action": t.action,
            "quantity": t.quantity,
            "price_at_trade": t.price_at_trade,
            "created_at": str(t.created_at),
        }
        for t in trades_result.scalars().all()
    ]

    # watchlist
    watchlist_result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == user_id)
    )
    watchlist = [
        {
            "ticker": w.ticker,
            "asset_type": w.asset_type,
            "notes": w.notes,
            "created_at": str(w.created_at),
        }
        for w in watchlist_result.scalars().all()
    ]

    # recent messages — last 20 across all sessions
    messages_result = await db.execute(
        select(ChatMessage)
        .join(DBSession, ChatMessage.session_id == DBSession.id)
        .where(DBSession.user_id == user_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(20)
    )
    messages = [
        {
            "role": m.role,
            "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
            "tools_used": m.tools_used,
            "created_at": str(m.created_at),
        }
        for m in messages_result.scalars().all()
    ]

    return UserDetail(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        trades=trades,
        watchlist=watchlist,
        recent_messages=messages,
    )



@router.patch("/users/{user_id}/disable")
async def disable_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Disable a user account. They can still log in but all requests return 403."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.flush()
    return {"message": f"{user.username} disabled"}


@router.patch("/users/{user_id}/enable")
async def enable_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Re-enable a disabled user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await db.flush()
    return {"message": f"{user.username} enabled"}


# ── Promote / demote ──────────────────────────────────────────────────────────

@router.patch("/users/{user_id}/promote")
async def promote_to_admin(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Promote a regular user to admin."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="User is already admin")

    user.role = UserRole.admin
    await db.flush()
    return {"message": f"{user.username} promoted to admin"}


@router.patch("/users/{user_id}/demote")
async def demote_from_admin(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Demote an admin to regular user."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole.user
    await db.flush()
    return {"message": f"{user.username} demoted to user"}



@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete a user and all their data.
    Cascade delete handles trades, watchlist, sessions, messages.
    """
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    return {"message": f"{user.username} permanently deleted"}



@router.get("/activity")
async def get_recent_activity(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """
    Recent platform activity — latest trades and messages across all users.
    Used for the admin activity feed.
    """
    trades_result = await db.execute(
        select(Trade, User.username)
        .join(User, Trade.user_id == User.id)
        .order_by(desc(Trade.created_at))
        .limit(limit)
    )
    trades = [
        {
            "type": "trade",
            "username": username,
            "detail": f"{t.action.upper()} {t.quantity} {t.ticker} @ ${t.price_at_trade:,.4f}",
            "created_at": str(t.created_at),
        }
        for t, username in trades_result.all()
    ]

    messages_result = await db.execute(
        select(ChatMessage, User.username)
        .join(DBSession, ChatMessage.session_id == DBSession.id)
        .join(User, DBSession.user_id == User.id)
        .where(ChatMessage.role == "user")
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )
    messages = [
        {
            "type": "message",
            "username": username,
            "detail": m.content[:100] + "..." if len(m.content) > 100 else m.content,
            "created_at": str(m.created_at),
        }
        for m, username in messages_result.all()
    ]

    # merge and sort by created_at
    activity = sorted(
        trades + messages,
        key=lambda x: x["created_at"],
        reverse=True
    )[:limit]

    return activity