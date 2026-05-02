from __future__ import annotations
from anthropic import AsyncAnthropic, AnthropicError
from providers.base import BaseProvider, GenerationSettings, GenerationResult, ProviderError
from config.settings import get_settings


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    model_map = {
        "fast": "claude-3-5-haiku-latest",
        "smart": "claude-3-5-sonnet-latest",
        "creative": "claude-3-5-sonnet-latest",
    }

    def __init__(self) -> None:
        s = get_settings()
        self._client = AsyncAnthropic(api_key=s.anthropic_api_key) if s.anthropic_api_key else None

    async def generate(self, messages, settings, model=None):
        if self._client is None:
            raise ProviderError("Anthropic API key not configured")
        mdl = self.resolve_model(settings.mode, model)
        temp = settings.temperature
        if temp is None:
            temp = 0.9 if settings.mode == "creative" else 0.3 if settings.mode == "smart" else 0.6
        # Anthropic separates system and accepts only user/assistant roles
        msgs = [{"role": ("assistant" if m.role == "assistant" else "user"), "content": m.content}
                for m in messages if m.role in ("user", "assistant")]
        try:
            resp = await self._client.messages.create(
                model=mdl,
                system=self.system_prompt(settings),
                messages=msgs,
                temperature=temp,
                max_tokens=settings.max_tokens or (256 if settings.style == "short" else 1024),
            )
        except AnthropicError as e:
            raise ProviderError(f"Anthropic error: {e}") from e
        text = "".join(getattr(b, "text", "") for b in resp.content)
        usage = resp.usage
        return GenerationResult(
            text=text,
            provider=self.name,
            model=mdl,
            prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(usage, "output_tokens", 0) or 0,
        )
