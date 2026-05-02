"""OpenAI-compatible HTTP provider base.

Used by GitHub Copilot, DeepSeek, xAI, OpenRouter, and any other backend that
speaks the OpenAI Chat Completions API shape.
"""
from __future__ import annotations
import aiohttp
from providers.base import BaseProvider, GenerationResult, ProviderError


class OpenAICompatibleProvider(BaseProvider):
    endpoint: str = ""        # full URL to /chat/completions
    api_key: str = ""
    extra_headers: dict[str, str] = {}
    requires_key: bool = True

    async def generate(self, messages, settings, model=None):
        if self.requires_key and not self.api_key:
            raise ProviderError(f"{self.name}: API key not configured")
        if not self.endpoint:
            raise ProviderError(f"{self.name}: endpoint not configured")

        mdl = model or self.resolve_model(settings.mode)
        temp = settings.temperature
        if temp is None:
            temp = 0.9 if settings.mode == "creative" else 0.4 if settings.mode == "smart" else 0.6

        sys_msg = [{"role": "system", "content": self.system_prompt(settings)}]
        body = {
            "model": mdl,
            "messages": sys_msg + [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temp,
            "max_tokens": settings.max_tokens or (256 if settings.style == "short" else 1024),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self.extra_headers)

        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(self.endpoint, json=body, headers=headers, timeout=120) as r:
                    txt = await r.text()
                    if r.status >= 400:
                        raise ProviderError(f"{self.name} HTTP {r.status}: {txt[:300]}")
                    import json as _json
                    data = _json.loads(txt)
        except aiohttp.ClientError as e:
            raise ProviderError(f"{self.name} network error: {e}") from e

        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"{self.name} bad response: {str(data)[:300]}") from e

        usage = data.get("usage") or {}
        return GenerationResult(
            text=text,
            provider=self.name,
            model=mdl,
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
        )
