from __future__ import annotations
from openai import AsyncOpenAI, OpenAIError
from providers.base import BaseProvider, ChatMessage, GenerationSettings, GenerationResult, ProviderError
from config.settings import get_settings


class OpenAIProvider(BaseProvider):
    name = "openai"
    model_map = {
        "fast": "gpt-4o-mini",
        "smart": "gpt-4o",
        "creative": "gpt-4o",
    }

    def __init__(self) -> None:
        s = get_settings()
        if not s.openai_api_key:
            self._client = None
        else:
            self._client = AsyncOpenAI(api_key=s.openai_api_key)

    async def generate(self, messages, settings, model=None):
        if self._client is None:
            raise ProviderError("OpenAI API key not configured")
        mdl = self.resolve_model(settings.mode, model)
        temp = settings.temperature
        if temp is None:
            temp = 0.9 if settings.mode == "creative" else 0.4 if settings.mode == "smart" else 0.6
        sys = [{"role": "system", "content": self.system_prompt(settings)}]
        body = sys + [{"role": m.role, "content": m.content} for m in messages]
        try:
            resp = await self._client.chat.completions.create(
                model=mdl,
                messages=body,
                temperature=temp,
                max_tokens=settings.max_tokens or (256 if settings.style == "short" else 1024),
            )
        except OpenAIError as e:
            raise ProviderError(f"OpenAI error: {e}") from e
        choice = resp.choices[0].message.content or ""
        usage = resp.usage
        return GenerationResult(
            text=choice,
            provider=self.name,
            model=mdl,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
