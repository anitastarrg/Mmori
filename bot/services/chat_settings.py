from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ChatSettings


DEFAULT_SETTINGS = ChatSettings(
	chat_id=0,
	chat_title=None,
	welcome_enabled=False,
	welcome_text="Добро пожаловать, {mention}!",
	rules_text=None,
	autodelete_welcome_seconds=0,
	profanity_filter_enabled=False,
	profanity_regex=None,
	profanity_words=None,
	link_filter_enabled=False,
	referral_domains=None,
	allowed_domains=None,
	link_mode="blocklist",
	link_allow_telegram=True,
	caps_threshold_percent=80,
	mention_limit=5,
	flood_messages=5,
	flood_interval_seconds=10,
	flood_burst=3,
	strict_newcomer_minutes=10,
	duplicates_filter_enabled=False,
	duplicates_window_seconds=30,
	duplicates_threshold=2,
	warn_threshold=3,
	warn_action="mute",
	punish_duration_seconds=3600,
	join_guard_enabled=False,
	join_guard_timeout_seconds=60,
	join_guard_message="Пожалуйста, подтвердите, что вы не бот, нажав кнопку ниже",
	block_stickers_enabled=False,
	block_forwards_enabled=False,
)


async def get_or_create_settings(session: AsyncSession, chat_id: int, chat_title: Optional[str]) -> ChatSettings:
	result = await session.execute(select(ChatSettings).where(ChatSettings.chat_id == chat_id))
	settings = result.scalar_one_or_none()
	if settings is None:
		settings = ChatSettings(
			chat_id=chat_id,
			chat_title=chat_title,
			welcome_enabled=DEFAULT_SETTINGS.welcome_enabled,
			welcome_text=DEFAULT_SETTINGS.welcome_text,
			rules_text=DEFAULT_SETTINGS.rules_text,
			autodelete_welcome_seconds=DEFAULT_SETTINGS.autodelete_welcome_seconds,
			profanity_filter_enabled=DEFAULT_SETTINGS.profanity_filter_enabled,
			profanity_regex=DEFAULT_SETTINGS.profanity_regex,
			profanity_words=DEFAULT_SETTINGS.profanity_words,
			link_filter_enabled=DEFAULT_SETTINGS.link_filter_enabled,
			referral_domains=DEFAULT_SETTINGS.referral_domains,
			allowed_domains=DEFAULT_SETTINGS.allowed_domains,
			link_mode=DEFAULT_SETTINGS.link_mode,
			link_allow_telegram=DEFAULT_SETTINGS.link_allow_telegram,
			caps_threshold_percent=DEFAULT_SETTINGS.caps_threshold_percent,
			mention_limit=DEFAULT_SETTINGS.mention_limit,
			flood_messages=DEFAULT_SETTINGS.flood_messages,
			flood_interval_seconds=DEFAULT_SETTINGS.flood_interval_seconds,
			flood_burst=DEFAULT_SETTINGS.flood_burst,
			strict_newcomer_minutes=DEFAULT_SETTINGS.strict_newcomer_minutes,
			duplicates_filter_enabled=DEFAULT_SETTINGS.duplicates_filter_enabled,
			duplicates_window_seconds=DEFAULT_SETTINGS.duplicates_window_seconds,
			duplicates_threshold=DEFAULT_SETTINGS.duplicates_threshold,
			warn_threshold=DEFAULT_SETTINGS.warn_threshold,
			warn_action=DEFAULT_SETTINGS.warn_action,
			punish_duration_seconds=DEFAULT_SETTINGS.punish_duration_seconds,
			join_guard_enabled=DEFAULT_SETTINGS.join_guard_enabled,
			join_guard_timeout_seconds=DEFAULT_SETTINGS.join_guard_timeout_seconds,
			join_guard_message=DEFAULT_SETTINGS.join_guard_message,
			block_stickers_enabled=DEFAULT_SETTINGS.block_stickers_enabled,
			block_forwards_enabled=DEFAULT_SETTINGS.block_forwards_enabled,
		)
		session.add(settings)
		await session.commit()
		await session.refresh(settings)
	return settings


async def update_settings(session: AsyncSession, chat_id: int, **kwargs) -> ChatSettings:
	result = await session.execute(select(ChatSettings).where(ChatSettings.chat_id == chat_id))
	settings = result.scalar_one()
	for key, value in kwargs.items():
		if hasattr(settings, key):
			setattr(settings, key, value)
	await session.commit()
	await session.refresh(settings)
	return settings