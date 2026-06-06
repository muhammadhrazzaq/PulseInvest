from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from langchain_core.messages import HumanMessage, AIMessage
from models.chat import ChatRequest, ChatResponse
from services.agent import run_agent
from db.database import get_db
from db.models import (
    User,
    Session as DBSession,
    ChatMessage,
    MessageRole as DBMessageRole,
)
from services.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Helpers ───────────────────────────────────────────────────────────────────


async def get_or_create_session(
    session_id: str,
    user: User,
    db: AsyncSession,
) -> DBSession:
    """
    Fetch existing session or create a new one.
    Ties the session_id from frontend to the logged-in user.
    """
    result = await db.execute(
        select(DBSession).where(DBSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        session = DBSession(session_id=session_id, user_id=user.id)
        db.add(session)
        await db.flush()
        await db.refresh(session)

    # security check — session must belong to this user
    if session.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="Session does not belong to this user"
        )

    return session


async def load_history_from_db(
    session: DBSession,
    db: AsyncSession,
) -> list:
    """
    Loads full chat history for a session from DB
    and converts to LangChain message objects.
    """
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    history = []
    for msg in messages:
        if msg.role == DBMessageRole.user:
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))

    return history


async def save_message(
    session: DBSession,
    role: DBMessageRole,
    content: str,
    tools_used: list[str],
    db: AsyncSession,
):
    """Persists a single message to the chat_messages table."""
    msg = ChatMessage(
        session_id=session.id,
        role=role,
        content=content,
        tools_used=",".join(tools_used) if tools_used else None,
    )
    db.add(msg)
    await db.flush()


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint.
    Loads history from DB, runs agent, saves both messages back to DB.
    """
    session = await get_or_create_session(request.session_id, current_user, db)

    # load history from DB — ignore history sent from frontend
    # DB is the single source of truth
    chat_history = await load_history_from_db(session, db)

    # run agent
    result = await run_agent(
        message=request.message,
        chat_history=chat_history,
    )

    # persist user message
    await save_message(
        session=session,
        role=DBMessageRole.user,
        content=request.message,
        tools_used=[],
        db=db,
    )

    # persist assistant reply
    await save_message(
        session=session,
        role=DBMessageRole.assistant,
        content=result["reply"],
        tools_used=result["tools_used"],
        db=db,
    )

    return ChatResponse(
        reply=result["reply"],
        session_id=request.session_id,
        tools_used=result["tools_used"],
    )


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full conversation history for a session.
    Streamlit calls this on page load to restore context.
    """
    result = await db.execute(
        select(DBSession).where(
            DBSession.session_id == session_id,
            DBSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        return {"session_id": session_id, "messages": []}

    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = messages_result.scalars().all()

    return {
        "session_id": session_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "tools_used": m.tools_used.split(",") if m.tools_used else [],
                "created_at": str(m.created_at),
            }
            for m in messages
        ],
    }


@router.get("/sessions")
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all sessions for the current user.
    Useful for showing conversation history list in the UI.
    """
    result = await db.execute(
        select(DBSession)
        .where(DBSession.user_id == current_user.id)
        .order_by(desc(DBSession.updated_at))
    )
    sessions = result.scalars().all()

    return [
        {
            "session_id": s.session_id,
            "created_at": str(s.created_at),
            "updated_at": str(s.updated_at),
        }
        for s in sessions
    ]


@router.delete("/history/{session_id}")
async def clear_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes all messages for a session.
    Keeps the session row itself — just wipes the messages.
    """
    result = await db.execute(
        select(DBSession).where(
            DBSession.session_id == session_id,
            DBSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id)
    )
    for msg in messages_result.scalars().all():
        await db.delete(msg)

    return {"session_id": session_id, "cleared": True}
