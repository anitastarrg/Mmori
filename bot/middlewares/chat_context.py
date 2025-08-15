from __future__ import annotations

from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.chat_settings import get_or_create_settings


class ChatContextMiddleware(BaseMiddleware):
	async def __call__(
		self,
		handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
		event: TelegramObject,
		data: Dict[str, Any],
	) -> Any:
		session: AsyncSession = data["session"]
		message: Message | None = data.get("event_chat_message") or data.get("message")  # support for filters
		chat = None
		if isinstance(event, Message):
			chat = event.chat
			message = event
		elif message is not None:
			chat = message.chat

		if chat is not None:
			settings = await get_or_create_settings(session, chat.id, chat.title)
			data["chat_settings"] = settings
		return await handler(event, data)