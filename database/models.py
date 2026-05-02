from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, Date, ForeignKey, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user_id
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))

    provider: Mapped[str] = mapped_column(String(32), default="github_copilot")
    model_id: Mapped[str | None] = mapped_column(String(64), default=None)
    # Per-provider last-picked model id, e.g. {"openai": "oa-gpt-4o", "anthropic": "an-sonnet-3-5"}
    last_models: Mapped[dict] = mapped_column(JSON, default=dict)

    mode: Mapped[str] = mapped_column(String(16), default="fast")
    style: Mapped[str] = mapped_column(String(16), default="short")
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_message_limit: Mapped[int | None] = mapped_column(Integer, default=None)
    daily_token_limit: Mapped[int | None] = mapped_column(Integer, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    usages: Mapped[list["DailyUsage"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="messages")


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    messages: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="usages")
