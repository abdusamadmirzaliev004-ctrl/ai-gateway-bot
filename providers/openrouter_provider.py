from __future__ import annotations
from providers.oai_compat import OpenAICompatibleProvider
from config.settings import get_settings


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"

    def __init__(self) -> None:
        s = get_settings()
        self.api_key = s.openrouter_api_key
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.extra_headers = {
            "HTTP-Referer": s.openrouter_referer or "https://github.com/ai-gateway-bot",
            "X-Title": s.openrouter_title or "AI Gateway Bot",
        }
        self.model_map = {
            "fast":     "openrouter/auto",
            "smart":    "anthropic/claude-3.5-sonnet",
            "creative": "openai/gpt-4o",
        }
