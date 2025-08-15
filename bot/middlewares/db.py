from __future__ import annotations

from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.db.session import get_session_maker


class DbSessionMiddleware(BaseMiddleware):
	def __init__(self) -> None:
		super().__init__()
		self._session_maker = get_session_maker()

	async def __call__(
		self,
		handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
		event: TelegramObject,
		data: Dict[str, Any],
	) -> Any:
		async with self._session_maker() as session:
			data["session"] = session
			return await handler(event, data)