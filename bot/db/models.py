from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


class ChatSettings(Base):
    __tablename__ = "chat_settings"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    welcome_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    autodelete_welcome_seconds: Mapped[int] = mapped_column(Integer, default=0)

    profanity_filter_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    profanity_regex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    link_filter_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_domains: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated

    caps_threshold_percent: Mapped[int] = mapped_column(Integer, default=80)
    mention_limit: Mapped[int] = mapped_column(Integer, default=5)

    flood_messages: Mapped[int] = mapped_column(Integer, default=5)
    flood_interval_seconds: Mapped[int] = mapped_column(Integer, default=10)

    warn_threshold: Mapped[int] = mapped_column(Integer, default=3)
    warn_action: Mapped[str] = mapped_column(String(16), default="mute")  # mute|ban|none
    punish_duration_seconds: Mapped[int] = mapped_column(Integer, default=3600)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    warnings: Mapped[list[UserWarning]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class UserWarning(Base):
    __tablename__ = "user_warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_settings.chat_id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chat: Mapped[ChatSettings] = relationship(back_populates="warnings")


class ActionLog(Base):
    __tablename__ = "action_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    moderator_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(32))  # delete|warn|mute|ban|unmute|unban
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)