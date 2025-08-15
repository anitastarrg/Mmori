from __future__ import annotations

import re
from typing import Iterable, Optional


def is_text_caps_excessive(text: str, threshold_percent: int) -> bool:
	letters = [ch for ch in text if ch.isalpha()]
	if not letters:
		return False
	caps = sum(1 for ch in letters if ch.isupper())
	percent = (caps / len(letters)) * 100
	return percent >= threshold_percent


def count_mentions(text: str) -> int:
	return text.count("@")


def contains_profanity(text: str, regex_pattern: Optional[str]) -> bool:
	if not regex_pattern:
		return False
	try:
		return re.search(regex_pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None
	except re.error:
		return False


def contains_profanity_words(text: str, words_csv: Optional[str]) -> bool:
	if not words_csv:
		return False
	words = [w.strip().lower() for w in words_csv.split(",") if w.strip()]
	txt = text.lower()
	return any(f" {w} " in f" {txt} " for w in words)


def contains_forbidden_link(text: str, domains_csv: Optional[str]) -> bool:
	if not domains_csv:
		return False
	domains = [d.strip().lower() for d in domains_csv.split(",") if d.strip()]
	text_lower = text.lower()
	return any(domain in text_lower for domain in domains)