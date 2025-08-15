from __future__ import annotations

import asyncio
import time
from typing import Dict, Tuple

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import ChatSettings
from bot.services import utils
from bot.services.moderation import (
	add_action_log,
	apply_punishment,
	increment_warning_and_check,
	reset_warning,
	unban,
	unmute,
)

router = Router(name=__name__)

# Simple in-memory flood tracker: { (chat_id, user_id): [timestamps...] }
_flood_tracker: Dict[Tuple[int, int], list[float]] = {}


async def delete_message_safe(message: Message) -> None:
	try:
		await message.delete()
	except Exception:
		pass


async def is_admin(message: Message) -> bool:
	member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
	return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.CREATOR}


@router.message(F.text)
async def content_filters(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	text = message.text or ""
	# Antiflood
	key = (message.chat.id, message.from_user.id)
	now = time.monotonic()
	bucket = _flood_tracker.setdefault(key, [])
	bucket.append(now)
	# cleanup
	window = chat_settings.flood_interval_seconds
	bucket[:] = [t for t in bucket if now - t <= window]
	if len(bucket) > chat_settings.flood_messages:
		await delete_message_safe(message)
		count = await increment_warning_and_check(session, chat_settings, message.from_user.id)
		if count >= chat_settings.warn_threshold:
			action = await apply_punishment(
				message.bot, session, chat_settings, message.from_user.id, message.from_user.id, "Антифлуд"
			)
			await reset_warning(session, chat_settings.chat_id, message.from_user.id)
			return
		return

	# Profanity regex
	if chat_settings.profanity_filter_enabled and utils.contains_profanity(text, chat_settings.profanity_regex):
		await delete_message_safe(message)
		await add_action_log(session, message.chat.id, message.from_user.id, "delete", message.from_user.id, "Нецензурная лексика")
		count = await increment_warning_and_check(session, chat_settings, message.from_user.id)
		if count >= chat_settings.warn_threshold:
			action = await apply_punishment(message.bot, session, chat_settings, message.from_user.id, message.from_user.id, "Мат")
			await reset_warning(session, chat_settings.chat_id, message.from_user.id)
		return

	# Profanity words
	if utils.contains_profanity_words(text, chat_settings.profanity_words):
		await delete_message_safe(message)
		await add_action_log(session, message.chat.id, message.from_user.id, "delete", message.from_user.id, "Запрещенные слова")
		return

	# Links
	if chat_settings.link_filter_enabled and utils.contains_forbidden_link(text, chat_settings.referral_domains):
		await delete_message_safe(message)
		await add_action_log(session, message.chat.id, message.from_user.id, "delete", message.from_user.id, "Ссылка запрещена")
		count = await increment_warning_and_check(session, chat_settings, message.from_user.id)
		if count >= chat_settings.warn_threshold:
			action = await apply_punishment(message.bot, session, chat_settings, message.from_user.id, message.from_user.id, "Запр. ссылка")
			await reset_warning(session, chat_settings.chat_id, message.from_user.id)
		return

	# CAPS
	if utils.is_text_caps_excessive(text, chat_settings.caps_threshold_percent):
		await delete_message_safe(message)
		await add_action_log(session, message.chat.id, message.from_user.id, "delete", message.from_user.id, "Много CAPS")
		return

	# Mentions
	if utils.count_mentions(text) > chat_settings.mention_limit:
		await delete_message_safe(message)
		await add_action_log(session, message.chat.id, message.from_user.id, "delete", message.from_user.id, "Спам упоминаниями")
		return


@router.message(F.sticker)
async def block_stickers(message: Message, chat_settings: ChatSettings) -> None:
	if chat_settings.block_stickers_enabled:
		await delete_message_safe(message)


@router.message(F.forward_origin)
async def block_forwards(message: Message, chat_settings: ChatSettings) -> None:
	if chat_settings.block_forwards_enabled:
		await delete_message_safe(message)


@router.message(Command("warn"))
async def cmd_warn(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	if not message.reply_to_message:
		await message.reply("Команда должна быть ответом на сообщение пользователя")
		return
	target = message.reply_to_message.from_user
	count = await increment_warning_and_check(session, chat_settings, target.id)
	await message.reply(f"Предупреждение {count}/{chat_settings.warn_threshold} для {target.full_name}")
	if count >= chat_settings.warn_threshold:
		action = await apply_punishment(message.bot, session, chat_settings, target.id, message.from_user.id, "Warn threshold")
		await reset_warning(session, chat_settings.chat_id, target.id)


@router.message(Command("mute"))
async def cmd_mute(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	if not message.reply_to_message:
		await message.reply("Нужно ответить на сообщение пользователя")
		return
	target = message.reply_to_message.from_user
	action = await apply_punishment(message.bot, session, chat_settings, target.id, message.from_user.id, "Manual mute")
	await message.reply(f"{action} применен к {target.full_name}")


@router.message(Command("ban"))
async def cmd_ban(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	if not message.reply_to_message:
		await message.reply("Нужно ответить на сообщение пользователя")
		return
	target = message.reply_to_message.from_user
	chat_settings.warn_action = "ban"
	action = await apply_punishment(message.bot, session, chat_settings, target.id, message.from_user.id, "Manual ban")
	await message.reply(f"{action} применен к {target.full_name}")


@router.message(Command("unmute"))
async def cmd_unmute(message: Message, session: AsyncSession) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	if not message.reply_to_message:
		await message.reply("Нужно ответить на сообщение пользователя")
		return
	target = message.reply_to_message.from_user
	ok = await unmute(message.bot, session, message.chat.id, target.id, message.from_user.id)
	await message.reply("Снят мут" if ok else "Не удалось снять мут")


@router.message(Command("unban"))
async def cmd_unban(message: Message, session: AsyncSession) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	if not message.reply_to_message:
		await message.reply("Нужно ответить на сообщение пользователя")
		return
	target = message.reply_to_message.from_user
	ok = await unban(message.bot, session, message.chat.id, target.id, message.from_user.id)
	await message.reply("Разбанен" if ok else "Не удалось разбанить")


@router.message(Command("purge"))
async def cmd_purge(message: Message) -> None:
	if not await is_admin(message):
		await message.reply("Только админы")
		return
	if not message.reply_to_message:
		await message.reply("Ответьте на первое сообщение для удаления до текущего")
		return
	start_id = message.reply_to_message.message_id
	end_id = message.message_id
	for msg_id in range(start_id, end_id + 1):
		try:
			await message.bot.delete_message(message.chat.id, msg_id)
		except Exception:
			pass