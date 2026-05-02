from __future__ import annotations
from providers.oai_compat import OpenAICompatibleProvider
from config.settings import get_settings


class XAIProvider(OpenAICompatibleProvider):
    name = "xai"

    def __init__(self) -> None:
        s = get_settings()
        self.api_key = s.xai_api_key
        self.endpoint = "https://api.x.ai/v1/chat/completions"
        self.model_map = {"fast": "grok-2-mini", "smart": "grok-2-latest", "creative": "grok-2-latest"}
