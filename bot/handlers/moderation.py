from __future__ import annotations

import asyncio
import time
import re
import urllib.parse
from collections import deque
from typing import Deque, Dict, Tuple, List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus, MessageEntityType
from aiogram.types import Message, MessageEntity
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

# Rate limiting state per (chat_id, user_id)
_rate_state: Dict[Tuple[int, int], Dict[str, float]] = {}
# Duplicate message history per (chat_id, user_id)
_dup_history: Dict[Tuple[int, int], Deque[Tuple[str, float]]] = {}


async def delete_message_safe(message: Message) -> None:
	try:
		await message.delete()
	except Exception:
		pass


async def is_admin(message: Message) -> bool:
	member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
	return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.CREATOR}


def _normalize_domain(domain: str) -> str:
	d = domain.strip().lower()
	if d.startswith("www."):
		d = d[4:]
	return d


def _extract_domains_from_message(message: Message) -> List[str]:
	text = message.text or message.caption or ""
	entities: List[MessageEntity] = []
	if message.entities:
		entities.extend(message.entities)
	if message.caption_entities:
		entities.extend(message.caption_entities)
	domains: List[str] = []
	for ent in entities:
		if ent.type in {MessageEntityType.URL, MessageEntityType.TEXT_LINK}:
			if ent.type == MessageEntityType.TEXT_LINK and ent.url:
				url = ent.url
			else:
				# slice url from text by offset/length
				url = text[ent.offset: ent.offset + ent.length]
			if not re.match(r"^[a-z]+://", url):
				url = "http://" + url
			try:
				parts = urllib.parse.urlsplit(url)
				domain = parts.hostname or ""
				if domain:
					domains.append(_normalize_domain(domain))
			except Exception:
				continue
	# fallback regex
	for m in re.finditer(r"https?://([^/\s]+)", text, flags=re.IGNORECASE):
		domains.append(_normalize_domain(m.group(1)))
	return list({d for d in domains if d})


def _is_telegram_domain(domain: str) -> bool:
	return domain in {"t.me", "telegram.me", "telegram.dog", "telega.one"}


def _is_newcomer_strict(key: Tuple[int, int], strict_minutes: int) -> bool:
	state = _rate_state.get(key)
	if not state:
		return True
	first_seen = state.get("first_seen", time.monotonic())
	return (time.monotonic() - first_seen) <= strict_minutes * 60


def _check_rate_limit(settings: ChatSettings, key: Tuple[int, int]) -> bool:
	# token bucket: capacity = flood_messages + flood_burst; refill rate = flood_messages per interval
	cap = float(settings.flood_messages + settings.flood_burst)
	rate_per_sec = settings.flood_messages / max(1, settings.flood_interval_seconds)
	state = _rate_state.setdefault(key, {"tokens": cap, "last": time.monotonic(), "first_seen": time.monotonic()})
	now = time.monotonic()
	# refill
	elapsed = now - state["last"]
	state["tokens"] = min(cap, state["tokens"] + elapsed * rate_per_sec)
	state["last"] = now
	# stricter for newcomers
	if _is_newcomer_strict(key, settings.strict_newcomer_minutes):
		# reduce available tokens by 50% for newcomers
		if state["tokens"] > cap * 0.5:
			state["tokens"] = cap * 0.5
	# consume
	if state["tokens"] >= 1.0:
		state["tokens"] -= 1.0
		return True
	return False


def _content_key(text: str) -> str:
	return re.sub(r"\s+", " ", (text or "").strip().lower())[:256]


def _check_duplicates(settings: ChatSettings, key: Tuple[int, int], text: str) -> bool:
	if not settings.duplicates_filter_enabled:
		return True
	if not text:
		return True
	window = settings.duplicates_window_seconds
	threshold = max(1, settings.duplicates_threshold)
	dq = _dup_history.setdefault(key, deque())
	now = time.monotonic()
	# purge old
	while dq and now - dq[0][1] > window:
		dq.popleft()
	ck = _content_key(text)
	# count
	cnt = sum(1 for k, _ in dq if k == ck)
	# add current
	dq.append((ck, now))
	return (cnt + 1) <= threshold


@router.message(F.text | F.caption)
async def content_filters(message: Message, session: AsyncSession, chat_settings: ChatSettings) -> None:
	text = message.text or message.caption or ""
	key = (message.chat.id, message.from_user.id)

	# Advanced anti-flood
	if not _check_rate_limit(chat_settings, key):
		await delete_message_safe(message)
		count = await increment_warning_and_check(session, chat_settings, message.from_user.id)
		if count >= chat_settings.warn_threshold:
			action = await apply_punishment(
				message.bot, session, chat_settings, message.from_user.id, message.from_user.id, "Антифлуд"
			)
			await reset_warning(session, chat_settings.chat_id, message.from_user.id)
		return

	# Duplicate messages
	if not _check_duplicates(chat_settings, key, text):
		await delete_message_safe(message)
		await add_action_log(session, message.chat.id, message.from_user.id, "delete", message.from_user.id, "Дублирование сообщений")
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

	# Links detection with allow/block lists
	if chat_settings.link_filter_enabled:
		domains = _extract_domains_from_message(message)
		if domains:
			blocked = False
			for d in domains:
				if chat_settings.link_allow_telegram and _is_telegram_domain(d):
					continue
				# allowlist mode
				if chat_settings.link_mode == "allowlist":
					allowed = { _normalize_domain(x) for x in (chat_settings.allowed_domains or "").split(",") if x.strip() }
					if d not in allowed:
						blocked = True
						break
				else:
					# blocklist mode with optional explicit allows
					allowed = { _normalize_domain(x) for x in (chat_settings.allowed_domains or "").split(",") if x.strip() }
					if d in allowed:
						continue
					blocked_domains = { _normalize_domain(x) for x in (chat_settings.referral_domains or "").split(",") if x.strip() }
					if any(d == bd or d.endswith("." + bd) for bd in blocked_domains):
						blocked = True
						break
			if blocked:
				await delete_message_safe(message)
				await add_action_log(session, message.chat.id, message.from_user.id, "delete", message.from_user.id, "Запрещенная ссылка")
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