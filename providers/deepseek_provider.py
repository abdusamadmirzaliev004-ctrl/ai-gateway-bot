from __future__ import annotations
from providers.oai_compat import OpenAICompatibleProvider
from config.settings import get_settings


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"

    def __init__(self) -> None:
        s = get_settings()
        self.api_key = s.deepseek_api_key
        self.endpoint = "https://api.deepseek.com/chat/completions"
        self.model_map = {"fast": "deepseek-chat", "smart": "deepseek-reasoner", "creative": "deepseek-chat"}
