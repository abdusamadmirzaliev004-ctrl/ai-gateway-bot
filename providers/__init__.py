from __future__ import annotations
from providers.base import BaseProvider, ChatMessage, GenerationSettings, GenerationResult, ProviderError
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider
from providers.github_copilot_provider import GitHubCopilotProvider
from providers.google_provider import GoogleGeminiProvider
from providers.xai_provider import XAIProvider
from providers.deepseek_provider import DeepSeekProvider
from providers.openrouter_provider import OpenRouterProvider
from providers.catalog import (
    PROVIDERS, ALL_MODELS, models_for, get_model, default_model_for, provider_label,
)
from config.settings import get_settings


_REGISTRY: dict[str, BaseProvider] = {}

_FACTORY = {
    "openai":         OpenAIProvider,
    "anthropic":      AnthropicProvider,
    "github_copilot": GitHubCopilotProvider,
    "google":         GoogleGeminiProvider,
    "xai":            XAIProvider,
    "deepseek":       DeepSeekProvider,
    "openrouter":     OpenRouterProvider,
}


def get_provider(name: str) -> BaseProvider:
    name = name.lower()
    if name not in _REGISTRY:
        if name not in _FACTORY:
            raise ProviderError(f"Unknown provider: {name}")
        _REGISTRY[name] = _FACTORY[name]()
    return _REGISTRY[name]


# Public surface re-exports
AVAILABLE_PROVIDERS = PROVIDERS  # [(key, label), ...]

MODES = [
    ("fast", "⚡ Fast"),
    ("smart", "🧠 Smart"),
    ("creative", "🎨 Creative"),
]
STYLES = [("short", "Short"), ("detailed", "Detailed")]


async def generate_response(
    prompt: str | list[ChatMessage],
    provider: str,
    model: str | None = None,
    settings: GenerationSettings | None = None,
    *,
    use_fallback: bool = True,
) -> GenerationResult:
    """Unified generation entrypoint.

    `model` here is the *API model name* (api_name from the catalog), not the
    catalog id. Handlers translate id -> api_name before calling this.
    """
    settings = settings or GenerationSettings()
    if isinstance(prompt, str):
        messages = [ChatMessage(role="user", content=prompt)]
    else:
        messages = prompt

    chain = [provider]
    if use_fallback:
        for p in get_settings().fallback_chain:
            if p and p not in chain:
                chain.append(p)

    last_err: Exception | None = None
    for i, name in enumerate(chain):
        try:
            prov = get_provider(name)
            # only pass explicit model on the first attempt (the user's selection)
            return await prov.generate(messages, settings, model=(model if i == 0 else None))
        except ProviderError as e:
            last_err = e
            continue
    raise ProviderError(f"All providers failed. Last error: {last_err}")


__all__ = [
    "generate_response", "get_provider", "AVAILABLE_PROVIDERS", "MODES", "STYLES",
    "ALL_MODELS", "models_for", "get_model", "default_model_for", "provider_label",
]
