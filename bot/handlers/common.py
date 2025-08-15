from __future__ import annotations

import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ChatSettings
from bot.services.join_guard import build_verify_keyboard, add_pending_and_schedule_kick, mark_joined, verify_user


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
	for user in message.new_chat_members:
		mark_joined(message.chat.id, user.id)
		if chat_settings.join_guard_enabled:
			mention = user.mention_html(user.full_name)
			text = (chat_settings.join_guard_message or "Пожалуйста, подтвердите, что вы не бот")
			kb = build_verify_keyboard(message.chat.id, user.id)
			sent = await message.answer(text, reply_markup=kb.as_markup())
			await add_pending_and_schedule_kick(message.bot, chat_settings, message.chat.id, user.id, sent.message_id)
		elif chat_settings.welcome_enabled:
			mention = user.mention_html(user.full_name)
			text = (chat_settings.welcome_text or "Добро пожаловать, {mention}!").format(mention=mention)
			sent = await message.answer(text)


@router.callback_query(F.data.startswith("verify:"))
async def cb_verify(callback: CallbackQuery) -> None:
	try:
		_, chat_id_s, user_id_s = callback.data.split(":", 2)
		chat_id = int(chat_id_s)
		user_id = int(user_id_s)
	except Exception:
		await callback.answer()
		return
	if callback.from_user.id != user_id:
		await callback.answer("Это не для вас", show_alert=True)
		return
	ok = await verify_user(callback.bot, chat_id, user_id)
	await callback.answer("Спасибо! Добро пожаловать" if ok else "Уже подтверждено")
	if callback.message:
		try:
			await callback.message.delete()
		except Exception:
			pass