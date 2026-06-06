from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from db.database import get_db
from db.models import User, UserRole, Session as DBSession
from services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    session_id: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None


# ── Register ──────────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    First user ever registered is automatically made admin.
    """

    # check email not taken
    existing_email = await db.execute(
        select(User).where(User.email == request.email.lower())
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # check username not taken
    existing_username = await db.execute(
        select(User).where(User.username == request.username.lower())
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    # validate password length
    if len(request.password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    # first user gets admin role automatically
    user_count = await db.execute(select(User))
    is_first_user = len(user_count.scalars().all()) == 0
    role = UserRole.admin if is_first_user else UserRole.user

    # create user
    user = User(
        email=request.email.lower(),
        username=request.username.lower(),
        hashed_password=hash_password(request.password),
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # create session
    session_id = str(uuid.uuid4())
    session = DBSession(session_id=session_id, user_id=user.id)
    db.add(session)
    await db.flush()

    # issue token
    token = create_access_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
        session_id=session_id,
    )


# ── Login ─────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Login with username + password.
    Returns JWT token + session id.
    OAuth2PasswordRequestForm expects form fields: username, password.
    """

    # find user by username
    result = await db.execute(
        select(User).where(User.username == form.username.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # update last login
    user.last_login = datetime.utcnow()
    await db.flush()

    # create new session for this login
    session_id = str(uuid.uuid4())
    session = DBSession(session_id=session_id, user_id=user.id)
    db.add(session)
    await db.flush()

    token = create_access_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
        session_id=session_id,
    )


# ── Me ────────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the currently logged-in user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


# ── Logout ────────────────────────────────────────────────────────────────────


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes the current session from DB.
    Frontend should also clear the JWT from session state.
    """
    result = await db.execute(
        select(DBSession).where(DBSession.user_id == current_user.id)
    )
    sessions = result.scalars().all()
    for session in sessions:
        await db.delete(session)

    return {"message": "Logged out successfully"}


# ── Change password ───────────────────────────────────────────────────────────


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    current_user.hashed_password = hash_password(request.new_password)
    await db.flush()

    return {"message": "Password changed successfully"}
