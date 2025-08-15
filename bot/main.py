from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.db.session import Base, get_engine
from bot.db.migrate import ensure_columns
from bot.handlers import admin as admin_handlers
from bot.handlers import common as common_handlers
from bot.handlers import moderation as moderation_handlers
from bot.logging_conf import setup_logging
from bot.middlewares.chat_context import ChatContextMiddleware
from bot.middlewares.db import DbSessionMiddleware


async def init_db() -> None:
	engine = get_engine()
	# ensure dir
	db_url = get_settings().db_url
	if db_url.startswith("sqlite+") and ":////" in db_url:
		path = "/" + db_url.split(":////", 1)[1]
		dirname = os.path.dirname(path)
		os.makedirs(dirname, exist_ok=True)
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
	await ensure_columns(engine)


async def main() -> None:
	settings = get_settings()
	setup_logging(settings.log_level)

	await init_db()

	if settings.dry_run:
		print("DRY_RUN=1: Import/DB OK. Exiting without polling.")
		return

	bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
	dp = Dispatcher()

	# Middlewares
	dp.update.middleware(DbSessionMiddleware())
	dp.update.middleware(ChatContextMiddleware())

	# Routers
	dp.include_router(common_handlers.router)
	dp.include_router(admin_handlers.router)
	dp.include_router(moderation_handlers.router)

	print("Bot is starting... Press Ctrl+C to stop.")
	await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
	try:
		asyncio.run(main())
	except (KeyboardInterrupt, SystemExit):
		print("Bot stopped")