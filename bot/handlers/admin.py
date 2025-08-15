from __future__ import annotations

import json
from aiogram import Router
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ChatSettings
from bot.services.chat_settings import update_settings


router = Router(name=__name__)


async def is_admin(message: Message) -> bool:
	member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
	return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


@router.message(Command("status"))
async def cmd_status(message: Message, chat_settings: ChatSettings) -> None:
	status_lines = [
		f"Welcome: {'ON' if chat_settings.welcome_enabled else 'OFF'}",
		f"Profanity: {'ON' if chat_settings.profanity_filter_enabled else 'OFF'}",
		f"Profanity words: {'set' if chat_settings.profanity_words else 'empty'}",
		f"Links: {'ON' if chat_settings.link_filter_enabled else 'OFF'} ({chat_settings.link_mode})",
		f"Allow Telegram links: {'YES' if chat_settings.link_allow_telegram else 'NO'}",
		f"Allowed domains: {chat_settings.allowed_domains or '-'}",
		f"Blocked domains: {chat_settings.referral_domains or '-'}",
		f"Stickers: {'BLOCK' if chat_settings.block_stickers_enabled else 'ALLOW'}",
		f"Forwards: {'BLOCK' if chat_settings.block_forwards_enabled else 'ALLOW'}",
		f"Join guard: {'ON' if chat_settings.join_guard_enabled else 'OFF'} ({chat_settings.join_guard_timeout_seconds}s)",
		f"Antiflood: msgs={chat_settings.flood_messages} interval={chat_settings.flood_interval_seconds}s burst={chat_settings.flood_burst} newcomer={chat_settings.strict_newcomer_minutes}m",
		f"Duplicates: {'ON' if chat_settings.duplicates_filter_enabled else 'OFF'} window={chat_settings.duplicates_window_seconds}s threshold={chat_settings.duplicates_threshold}",
		f"Warn threshold: {chat_settings.warn_threshold} -> {chat_settings.warn_action} ({chat_settings.punish_duration_seconds}s)",
		f"CAPS: >={chat_settings.caps_threshold_percent}%",
		f"Mentions limit: {chat_settings.mention_limit}",
	]
	await message.reply("\n".join(status_lines))


@router.message(Command("config"))
async def cmd_config(message: Message, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы могут настраивать бота")
		return
	kb = InlineKeyboardBuilder()
	kb.button(text=f"Welcome: {'ON' if chat_settings.welcome_enabled else 'OFF'}", callback_data="toggle_welcome")
	kb.button(text=f"Profanity: {'ON' if chat_settings.profanity_filter_enabled else 'OFF'}", callback_data="toggle_profanity")
	kb.button(text=f"Links: {'ON' if chat_settings.link_filter_enabled else 'OFF'}", callback_data="toggle_links")
	kb.button(text=f"Stickers: {'BLOCK' if chat_settings.block_stickers_enabled else 'ALLOW'}", callback_data="toggle_stickers")
	kb.button(text=f"Forwards: {'BLOCK' if chat_settings.block_forwards_enabled else 'ALLOW'}", callback_data="toggle_forwards")
	kb.button(text=f"Join guard: {'ON' if chat_settings.join_guard_enabled else 'OFF'}", callback_data="toggle_join_guard")
	kb.adjust(1)
	await message.reply(
		"Настройки чата:\n"
		"/setflood <msgs> <seconds> <burst>\n"
		"/setnewcomer <minutes>\n"
		"/setduplicates <on|off> <window_sec> <threshold>\n"
		"/setwarn <threshold> <mute|ban|none> <seconds>\n"
		"/setcaps <percent>\n"
		"/setmentions <count>\n"
		"/setprofanityregex <pattern>\n"
		"/setprofanitywords <w1,w2,...>\n"
		"/setlinks <blocklist|allowlist>\n"
		"/setallowdomains <d1,d2,...>\n"
		"/setblockdomains <d1,d2,...>\n"
		"/allowtglinks <on|off>\n"
		"/setrefdomains <domain1,domain2,...>\n"
		"/setjoinguard <on|off> <timeout_seconds>\n"
		"Export/Import — кнопки ниже",
		reply_markup=kb.as_markup(),
	)


@router.callback_query(lambda c: c.data in {"toggle_welcome", "toggle_profanity", "toggle_links", "toggle_stickers", "toggle_forwards", "toggle_join_guard"})
async def toggles(callback: CallbackQuery, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not callback.message:
		return
	if not await is_admin(callback.message):
		await callback.answer("Только админы", show_alert=True)
		return
	field_map = {
		"toggle_welcome": ("welcome_enabled", not chat_settings.welcome_enabled),
		"toggle_profanity": ("profanity_filter_enabled", not chat_settings.profanity_filter_enabled),
		"toggle_links": ("link_filter_enabled", not chat_settings.link_filter_enabled),
		"toggle_stickers": ("block_stickers_enabled", not chat_settings.block_stickers_enabled),
		"toggle_forwards": ("block_forwards_enabled", not chat_settings.block_forwards_enabled),
		"toggle_join_guard": ("join_guard_enabled", not chat_settings.join_guard_enabled),
	}
	field, new_val = field_map[callback.data]
	await update_settings(session, chat_settings.chat_id, **{field: new_val})
	await callback.answer("Сохранено")
	await callback.message.delete()


@router.message(Command("setwelcome"))
async def cmd_setwelcome(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	text = message.text.split(maxsplit=1)
	if len(text) < 2:
		await message.reply("Использование: /setwelcome Текст приветствия. Доступные плейсхолдеры: {mention}")
		return
	await update_settings(session, chat_settings.chat_id, welcome_text=text[1], welcome_enabled=True)
	await message.reply("Приветствие обновлено")


@router.message(Command("setrules"))
async def cmd_setrules(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	text = message.text.split(maxsplit=1)
	if len(text) < 2:
		await message.reply("Использование: /setrules Текст правил")
		return
	await update_settings(session, chat_settings.chat_id, rules_text=text[1])
	await message.reply("Правила обновлены")


@router.message(Command("setflood"))
async def cmd_setflood(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split()
	if len(parts) != 4 or not all(p.isdigit() for p in parts[1:]):
		await message.reply("Использование: /setflood <msgs> <seconds> <burst>")
		return
	await update_settings(session, chat_settings.chat_id, flood_messages=int(parts[1]), flood_interval_seconds=int(parts[2]), flood_burst=int(parts[3]))
	await message.reply("Антифлуд обновлен")


@router.message(Command("setnewcomer"))
async def cmd_setnewcomer(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split()
	if len(parts) != 2 or not parts[1].isdigit():
		await message.reply("Использование: /setnewcomer <minutes>")
		return
	await update_settings(session, chat_settings.chat_id, strict_newcomer_minutes=int(parts[1]))
	await message.reply("Усиление для новичков обновлено")


@router.message(Command("setduplicates"))
async def cmd_setduplicates(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split()
	if len(parts) != 4 or parts[1] not in {"on", "off"} or not parts[2].isdigit() or not parts[3].isdigit():
		await message.reply("Использование: /setduplicates <on|off> <window_sec> <threshold>")
		return
	await update_settings(session, chat_settings.chat_id, duplicates_filter_enabled=(parts[1] == "on"), duplicates_window_seconds=int(parts[2]), duplicates_threshold=int(parts[3]))
	await message.reply("Фильтр дублей обновлен")


@router.message(Command("setlinks"))
async def cmd_setlinks(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split()
	if len(parts) != 2 or parts[1] not in {"blocklist", "allowlist"}:
		await message.reply("Использование: /setlinks <blocklist|allowlist>")
		return
	await update_settings(session, chat_settings.chat_id, link_mode=parts[1])
	await message.reply("Режим фильтра ссылок обновлен")


@router.message(Command("setallowdomains"))
async def cmd_setallowdomains(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split(maxsplit=1)
	if len(parts) != 2:
		await message.reply("Использование: /setallowdomains <d1,d2,...>")
		return
	await update_settings(session, chat_settings.chat_id, allowed_domains=parts[1])
	await message.reply("Список разрешенных доменов обновлен")


@router.message(Command("setblockdomains"))
async def cmd_setblockdomains(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split(maxsplit=1)
	if len(parts) != 2:
		await message.reply("Использование: /setblockdomains <d1,d2,...>")
		return
	await update_settings(session, chat_settings.chat_id, referral_domains=parts[1])
	await message.reply("Список запрещенных доменов обновлен")


@router.message(Command("allowtglinks"))
async def cmd_allowtglinks(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split()
	if len(parts) != 2 or parts[1] not in {"on", "off"}:
		await message.reply("Использование: /allowtglinks <on|off>")
		return
	await update_settings(session, chat_settings.chat_id, link_allow_telegram=(parts[1] == "on"))
	await message.reply("Разрешение на ссылки Telegram обновлено")


@router.message(Command("setprofanityregex"))
async def cmd_setprofanityregex(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split(maxsplit=1)
	if len(parts) != 2:
		await message.reply("Использование: /setprofanityregex <pattern>")
		return
	await update_settings(session, chat_settings.chat_id, profanity_regex=parts[1], profanity_filter_enabled=True)
	await message.reply("Регулярное выражение мата обновлено")


@router.message(Command("setprofanitywords"))
async def cmd_setprofanitywords(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split(maxsplit=1)
	if len(parts) != 2:
		await message.reply("Использование: /setprofanitywords <w1,w2,...>")
		return
	await update_settings(session, chat_settings.chat_id, profanity_words=parts[1])
	await message.reply("Список запрещенных слов обновлен")


@router.message(Command("setrefdomains"))
async def cmd_setrefdomains(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split(maxsplit=1)
	if len(parts) != 2:
		await message.reply("Использование: /setrefdomains <domain1,domain2,...>")
		return
	await update_settings(session, chat_settings.chat_id, referral_domains=parts[1], link_filter_enabled=True)
	await message.reply("Список запрещенных доменов обновлен")


@router.message(Command("setjoinguard"))
async def cmd_setjoinguard(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	parts = message.text.split()
	if len(parts) != 3 or parts[1] not in {"on", "off"} or not parts[2].isdigit():
		await message.reply("Использование: /setjoinguard <on|off> <timeout_seconds>")
		return
	await update_settings(
		session,
		chat_settings.chat_id,
		join_guard_enabled=(parts[1] == "on"),
		join_guard_timeout_seconds=int(parts[2]),
	)
	await message.reply("Join guard обновлен")


@router.callback_query(lambda c: c.data == "export_settings")
async def cb_export(callback: CallbackQuery, chat_settings: ChatSettings) -> None:
	if not callback.message:
		return
	if not await is_admin(callback.message):
		await callback.answer("Только админы", show_alert=True)
		return
	data = {
		"welcome_enabled": chat_settings.welcome_enabled,
		"welcome_text": chat_settings.welcome_text,
		"rules_text": chat_settings.rules_text,
		"autodelete_welcome_seconds": chat_settings.autodelete_welcome_seconds,
		"profanity_filter_enabled": chat_settings.profanity_filter_enabled,
		"profanity_regex": chat_settings.profanity_regex,
		"profanity_words": chat_settings.profanity_words,
		"link_filter_enabled": chat_settings.link_filter_enabled,
		"referral_domains": chat_settings.referral_domains,
		"allowed_domains": chat_settings.allowed_domains,
		"link_mode": chat_settings.link_mode,
		"link_allow_telegram": chat_settings.link_allow_telegram,
		"caps_threshold_percent": chat_settings.caps_threshold_percent,
		"mention_limit": chat_settings.mention_limit,
		"flood_messages": chat_settings.flood_messages,
		"flood_interval_seconds": chat_settings.flood_interval_seconds,
		"flood_burst": chat_settings.flood_burst,
		"strict_newcomer_minutes": chat_settings.strict_newcomer_minutes,
		"duplicates_filter_enabled": chat_settings.duplicates_filter_enabled,
		"duplicates_window_seconds": chat_settings.duplicates_window_seconds,
		"duplicates_threshold": chat_settings.duplicates_threshold,
		"warn_threshold": chat_settings.warn_threshold,
		"warn_action": chat_settings.warn_action,
		"punish_duration_seconds": chat_settings.punish_duration_seconds,
		"join_guard_enabled": chat_settings.join_guard_enabled,
		"join_guard_timeout_seconds": chat_settings.join_guard_timeout_seconds,
		"join_guard_message": chat_settings.join_guard_message,
		"block_stickers_enabled": chat_settings.block_stickers_enabled,
		"block_forwards_enabled": chat_settings.block_forwards_enabled,
	}
	as_text = json.dumps(data, ensure_ascii=False, indent=2)
	await callback.message.answer_document(BufferedInputFile(as_text.encode("utf-8"), filename="chat_settings.json"))
	await callback.answer()


@router.callback_query(lambda c: c.data == "import_settings")
async def cb_import(callback: CallbackQuery) -> None:
	await callback.answer("Пришлите .json файл реплаем на это сообщение", show_alert=True)


@router.message()
async def import_settings_file(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	# Handle JSON file sent in reply to previous prompt
	if not (message.reply_to_message and message.document):
		return
	if not message.reply_to_message.from_user or not message.reply_to_message.from_user.is_bot:
		return
	me = await message.bot.me()
	if message.reply_to_message.from_user.id != me.id:
		return
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	try:
		file = await message.bot.get_file(message.document.file_id)
		content = await message.bot.download_file(file.file_path)
		data = json.loads(content.read().decode("utf-8"))
		await update_settings(session, chat_settings.chat_id, **data)
		await message.reply("Настройки импортированы")
	except Exception:
		await message.reply("Не удалось импортировать файл. Проверьте формат JSON.")