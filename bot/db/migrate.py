from __future__ import annotations

from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_columns(engine: AsyncEngine) -> None:
	async with engine.begin() as conn:
		# fetch existing columns
		res = await conn.execute(text("PRAGMA table_info('chat_settings')"))
		cols = {row[1] for row in res.fetchall()}  # type: ignore[index]
		alter_statements: list[str] = []
		def add(stmt: str) -> None:
			alter_statements.append(stmt)

		if "profanity_words" not in cols:
			add("ALTER TABLE chat_settings ADD COLUMN profanity_words TEXT")
		if "join_guard_enabled" not in cols:
			add("ALTER TABLE chat_settings ADD COLUMN join_guard_enabled BOOLEAN DEFAULT 0")
		if "join_guard_timeout_seconds" not in cols:
			add("ALTER TABLE chat_settings ADD COLUMN join_guard_timeout_seconds INTEGER DEFAULT 60")
		if "join_guard_message" not in cols:
			add("ALTER TABLE chat_settings ADD COLUMN join_guard_message TEXT")
		if "block_stickers_enabled" not in cols:
			add("ALTER TABLE chat_settings ADD COLUMN block_stickers_enabled BOOLEAN DEFAULT 0")
		if "block_forwards_enabled" not in cols:
			add("ALTER TABLE chat_settings ADD COLUMN block_forwards_enabled BOOLEAN DEFAULT 0")

		for stmt in alter_statements:
			await conn.execute(text(stmt))