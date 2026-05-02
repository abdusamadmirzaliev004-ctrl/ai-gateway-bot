"""Google Gemini native API provider (generateContent)."""
from __future__ import annotations
import aiohttp
from providers.base import BaseProvider, GenerationResult, ProviderError
from config.settings import get_settings


class GoogleGeminiProvider(BaseProvider):
    name = "google"
    model_map = {
        "fast":     "gemini-1.5-flash",
        "smart":    "gemini-1.5-pro",
        "creative": "gemini-1.5-pro",
    }

    def __init__(self) -> None:
        self._key = get_settings().google_api_key

    async def generate(self, messages, settings, model=None):
        if not self._key:
            raise ProviderError("Google: GOOGLE_API_KEY not configured")
        mdl = self.resolve_model(settings.mode, model)
        temp = settings.temperature
        if temp is None:
            temp = 0.9 if settings.mode == "creative" else 0.4 if settings.mode == "smart" else 0.6

        # Convert to Gemini "contents" shape; system goes via system_instruction
        contents = []
        for m in messages:
            if m.role not in ("user", "assistant"):
                continue
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        body = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": self.system_prompt(settings)}]},
            "generationConfig": {
                "temperature": temp,
                "maxOutputTokens": settings.max_tokens or (256 if settings.style == "short" else 1024),
            },
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent?key={self._key}"
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(url, json=body, timeout=120) as r:
                    txt = await r.text()
                    if r.status >= 400:
                        raise ProviderError(f"Google HTTP {r.status}: {txt[:300]}")
                    import json as _json
                    data = _json.loads(txt)
        except aiohttp.ClientError as e:
            raise ProviderError(f"Google network error: {e}") from e

        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"Google bad response: {str(data)[:300]}") from e

        usage = data.get("usageMetadata") or {}
        return GenerationResult(
            text=text,
            provider=self.name,
            model=mdl,
            prompt_tokens=usage.get("promptTokenCount", 0) or 0,
            completion_tokens=usage.get("candidatesTokenCount", 0) or 0,
        )
