import enum
from sqlalchemy import (
    Column, Integer, String, Float,
    DateTime, Boolean, Text, ForeignKey,
    Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

class AssetType(str, enum.Enum):
    stock = "stock"
    crypto = "crypto"

class TradeAction(str, enum.Enum):
    buy = "buy"
    sell = "sell"

class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String, unique=True, nullable=False, index=True)
    username         = Column(String, unique=True, nullable=False, index=True)
    hashed_password  = Column(String, nullable=False)
    role             = Column(SAEnum(UserRole), default=UserRole.user, nullable=False)
    is_active        = Column(Boolean, default=True, nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    last_login       = Column(DateTime(timezone=True), nullable=True)

    # relationships
    sessions         = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    trades           = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    watchlist        = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(String, unique=True, nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    user         = relationship("User", back_populates="sessions")
    messages     = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role        = Column(SAEnum(MessageRole), nullable=False)
    content     = Column(Text, nullable=False)
    tools_used  = Column(String, nullable=True)  # comma-separated tool names
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    session     = relationship("Session", back_populates="messages")


class Trade(Base):
    __tablename__ = "trades"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker           = Column(String, nullable=False, index=True)
    asset_type       = Column(SAEnum(AssetType), nullable=False)
    action           = Column(SAEnum(TradeAction), nullable=False)
    quantity         = Column(Float, nullable=False)
    price_at_trade   = Column(Float, nullable=False)
    notes            = Column(String, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user             = relationship("User", back_populates="trades")


class Watchlist(Base):
    __tablename__ = "watchlist"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker      = Column(String, nullable=False, index=True)
    asset_type  = Column(SAEnum(AssetType), nullable=False)
    notes       = Column(String, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user        = relationship("User", back_populates="watchlist")