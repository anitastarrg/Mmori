from __future__ import annotations

import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ChatSettings


router = Router(name=__name__)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
	await message.reply("Я модератор-бот. Добавьте меня в группу и дайте права админа для работы.")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
	await message.reply(
		"""
Команды:
/config — открыть меню настроек (для администраторов)
/status — текущее состояние фильтров
/rules — показать правила чата
/warn, /mute, /ban, /unmute, /unban — модерация по реплаю
		""".strip()
	)


@router.message(Command("rules"))
async def cmd_rules(message: Message, chat_settings: ChatSettings) -> None:
	if chat_settings.rules_text:
		await message.reply(chat_settings.rules_text)
	else:
		await message.reply("Правила не заданы. Используйте /setrules в чате.")


@router.message(F.new_chat_members)
async def new_members(message: Message, chat_settings: ChatSettings) -> None:
	if not chat_settings.welcome_enabled:
		return
	for user in message.new_chat_members:
		mention = user.mention_html(user.full_name)
		text = (chat_settings.welcome_text or "Добро пожаловать, {mention}!").format(mention=mention)
		sent = await message.answer(text)
		if chat_settings.autodelete_welcome_seconds > 0:
			async def delayed_delete(msg: Message, delay: int) -> None:
				await asyncio.sleep(delay)
				try:
					await msg.delete()
				except Exception:
					pass
			asyncio.create_task(delayed_delete(sent, chat_settings.autodelete_welcome_seconds))