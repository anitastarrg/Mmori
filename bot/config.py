from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	bot_token: str = Field(..., alias="BOT_TOKEN")
	db_url: str = Field("sqlite+aiosqlite:////workspace/data/bot.db", alias="DB_URL")
	admins: List[int] = Field(default_factory=list, alias="ADMINS")
	log_level: str = Field("INFO", alias="LOG_LEVEL")
	redis_url: Optional[str] = Field(None, alias="REDIS_URL")
	dry_run: bool = Field(False, alias="DRY_RUN")

	@validator("admins", pre=True)
	def parse_admins(cls, v: str | List[int] | None) -> List[int]:
		if v is None:
			return []
		if isinstance(v, list):
			return [int(x) for x in v]
		if isinstance(v, str):
			v = v.strip()
			if not v:
				return []
			return [int(x.strip()) for x in v.split(",") if x.strip()]
		return []

	class Config:
		env_file = ".env"
		env_file_encoding = "utf-8"
		case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()  # type: ignore[call-arg]