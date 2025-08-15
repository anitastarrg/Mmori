from __future__ import annotations

from datetime import timedelta
from typing import Optional

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatPermissions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ActionLog, ChatSettings, UserWarning


async def add_action_log(session: AsyncSession, chat_id: int, target_user_id: int, action: str, moderator_user_id: Optional[int], reason: Optional[str]) -> None:
	log = ActionLog(
		chat_id=chat_id,
		target_user_id=target_user_id,
		moderator_user_id=moderator_user_id,
		action=action,
		reason=reason,
	)
	session.add(log)
	await session.commit()


async def get_user_warning(session: AsyncSession, chat_id: int, user_id: int) -> UserWarning:
	result = await session.execute(
		select(UserWarning).where(UserWarning.chat_id == chat_id, UserWarning.user_id == user_id)
	)
	warning = result.scalar_one_or_none()
	if warning is None:
		warning = UserWarning(chat_id=chat_id, user_id=user_id, count=0)
		session.add(warning)
		await session.commit()
		await session.refresh(warning)
	return warning


async def increment_warning_and_check(session: AsyncSession, chat_settings: ChatSettings, user_id: int) -> int:
	warning = await get_user_warning(session, chat_settings.chat_id, user_id)
	warning.count += 1
	await session.commit()
	return warning.count


async def reset_warning(session: AsyncSession, chat_id: int, user_id: int) -> None:
	result = await session.execute(
		select(UserWarning).where(UserWarning.chat_id == chat_id, UserWarning.user_id == user_id)
	)
	warning = result.scalar_one_or_none()
	if warning is not None:
		warning.count = 0
		await session.commit()


async def apply_punishment(bot: Bot, session: AsyncSession, chat_settings: ChatSettings, user_id: int, moderator_id: Optional[int], reason: Optional[str]) -> str:
	action = chat_settings.warn_action
	if action == "none":
		return "none"

	duration = chat_settings.punish_duration_seconds
	try:
		if action == "mute":
			permissions = ChatPermissions(can_send_messages=False)
			until_date = timedelta(seconds=duration)
			await bot.restrict_chat_member(chat_settings.chat_id, user_id, permissions=permissions, until_date=until_date)
			await add_action_log(session, chat_settings.chat_id, user_id, "mute", moderator_id, reason)
			return "mute"
		elif action == "ban":
			await bot.ban_chat_member(chat_settings.chat_id, user_id, until_date=None)
			await add_action_log(session, chat_settings.chat_id, user_id, "ban", moderator_id, reason)
			return "ban"
	except TelegramBadRequest:
		return "error"
	return "none"


async def unmute(bot: Bot, session: AsyncSession, chat_id: int, user_id: int, moderator_id: Optional[int]) -> bool:
	try:
		permissions = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True, can_change_info=False, can_invite_users=True, can_pin_messages=False)
		await bot.restrict_chat_member(chat_id, user_id, permissions=permissions)
		await add_action_log(session, chat_id, user_id, "unmute", moderator_id, None)
		return True
	except TelegramBadRequest:
		return False


async def unban(bot: Bot, session: AsyncSession, chat_id: int, user_id: int, moderator_id: Optional[int]) -> bool:
	try:
		await bot.unban_chat_member(chat_id, user_id)
		await add_action_log(session, chat_id, user_id, "unban", moderator_id, None)
		return True
	except TelegramBadRequest:
		return False