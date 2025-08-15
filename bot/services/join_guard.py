from __future__ import annotations

import asyncio
import time
from typing import Dict, Tuple, Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ChatSettings
from bot.db.session import get_session_maker
from bot.services.moderation import add_action_log


_Pending = Dict[Tuple[int, int], Dict[str, int]]
_JoinedAt = Dict[Tuple[int, int], float]

_pending: _Pending = {}
_joined_at: _JoinedAt = {}


def mark_joined(chat_id: int, user_id: int) -> None:
	_joined_at[(chat_id, user_id)] = time.time()


def get_join_time(chat_id: int, user_id: int) -> Optional[float]:
	return _joined_at.get((chat_id, user_id))


def is_pending(chat_id: int, user_id: int) -> bool:
	return (chat_id, user_id) in _pending


def build_verify_keyboard(chat_id: int, user_id: int) -> InlineKeyboardBuilder:
	kb = InlineKeyboardBuilder()
	kb.row(InlineKeyboardButton(text="Я не бот", callback_data=f"verify:{chat_id}:{user_id}"))
	return kb


async def add_pending_and_schedule_kick(bot: Bot, chat_settings: ChatSettings, chat_id: int, user_id: int, message_id: int) -> None:
	# Store verification message id
	_pending[(chat_id, user_id)] = {"message_id": message_id}
	# Schedule task
	async def task():
		await asyncio.sleep(max(5, chat_settings.join_guard_timeout_seconds))
		# If still pending -> kick
		if (chat_id, user_id) in _pending:
			try:
				await bot.ban_chat_member(chat_id, user_id)
			except Exception:
				pass
			# Log kick
			try:
				SessionMaker = get_session_maker()
				async with SessionMaker() as session:
					await add_action_log(session, chat_id, user_id, "kick", None, "Join guard timeout")
			except Exception:
				pass
			_pending.pop((chat_id, user_id), None)
	asyncio.create_task(task())


async def verify_user(bot: Bot, chat_id: int, user_id: int) -> bool:
	entry = _pending.pop((chat_id, user_id), None)
	if not entry:
		return False
	# Delete verify message
	msg_id = entry.get("message_id")
	if msg_id:
		try:
			await bot.delete_message(chat_id, msg_id)
		except Exception:
			pass
	return True