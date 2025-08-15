from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
	numeric_level = getattr(logging, level.upper(), logging.INFO)
	logging.basicConfig(
		level=numeric_level,
		format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
		stream=sys.stdout,
	)