from __future__ import annotations
from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str = Field(..., alias="BOT_TOKEN")
    webhook_url: str = Field("", alias="WEBHOOK_URL")
    webhook_path: str = Field("/tg/webhook", alias="WEBHOOK_PATH")
    webhook_secret: str = Field("", alias="WEBHOOK_SECRET")
    webapp_host: str = Field("0.0.0.0", alias="WEBAPP_HOST")
    webapp_port: int = Field(8080, alias="WEBAPP_PORT")

    # DB
    database_url: str = Field("sqlite+aiosqlite:///./data/bot.db", alias="DATABASE_URL")

    # Admins
    admin_ids_raw: str = Field("", alias="ADMIN_IDS")

    # Defaults
    default_provider: str = Field("github_copilot", alias="DEFAULT_PROVIDER")
    default_mode: str = Field("fast", alias="DEFAULT_MODE")

    # Quotas
    daily_message_limit: int = Field(50, alias="DAILY_MESSAGE_LIMIT")
    daily_token_limit: int = Field(100_000, alias="DAILY_TOKEN_LIMIT")
    rate_limit_per_minute: int = Field(10, alias="RATE_LIMIT_PER_MINUTE")

    # Fallback chain
    fallback_chain_raw: str = Field("github_copilot,openai,anthropic", alias="FALLBACK_CHAIN")

    # Provider keys
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")

    github_copilot_token: str = Field("", alias="GITHUB_COPILOT_TOKEN")
    github_copilot_endpoint: str = Field("https://api.githubcopilot.com/chat/completions",
                                         alias="GITHUB_COPILOT_ENDPOINT")

    google_api_key: str = Field("", alias="GOOGLE_API_KEY")
    xai_api_key: str = Field("", alias="XAI_API_KEY")
    deepseek_api_key: str = Field("", alias="DEEPSEEK_API_KEY")

    openrouter_api_key: str = Field("", alias="OPENROUTER_API_KEY")
    openrouter_referer: str = Field("", alias="OPENROUTER_REFERER")
    openrouter_title: str = Field("", alias="OPENROUTER_TITLE")

    @property
    def admin_ids(self) -> List[int]:
        return [int(x) for x in self.admin_ids_raw.split(",") if x.strip().isdigit()]

    @property
    def fallback_chain(self) -> List[str]:
        return [x.strip() for x in self.fallback_chain_raw.split(",") if x.strip()]

    @property
    def use_webhook(self) -> bool:
        return bool(self.webhook_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
