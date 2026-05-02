"""Catalog of providers and their models.

Single source of truth for the UI selector + per-user persisted model choice.

Each Model:
  id          stable internal id (used in DB + callback_data; <=64 chars)
  api_name    string passed to the provider's API
  label       short display name shown in the inline keyboard
  description one-line description
  tags        short tags shown next to the label (fast/smart/coding/etc.)
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Model:
    id: str
    provider: str
    api_name: str
    label: str
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)


# Order matters — first model of a provider is its default.
_CATALOG: list[Model] = [
    # ---------- GitHub Copilot Pro+ ----------
    Model("gh-claude-opus-4-7",       "github_copilot", "claude-opus-4.7",         "Claude Opus 4.7",        "Anthropic flagship via Copilot — strongest reasoning",            ("smart", "long-context")),
    Model("gh-claude-sonnet-4-6",     "github_copilot", "claude-sonnet-4.6",       "Claude Sonnet 4.6",      "Balanced Anthropic model — fast + capable",                       ("balanced",)),
    Model("gh-claude-sonnet-4-5",     "github_copilot", "claude-sonnet-4.5",       "Claude Sonnet 4.5",      "Previous Sonnet — stable",                                        ("balanced",)),
    Model("gh-claude-opus-4-5",       "github_copilot", "claude-opus-4.5",         "Claude Opus 4.5",        "Previous Opus — heavy reasoning",                                 ("smart",)),
    Model("gh-claude-haiku-4-5",      "github_copilot", "claude-haiku-4.5",        "Claude Haiku 4.5",       "Smallest Anthropic — very fast, cheap",                           ("fast", "cheap")),
    Model("gh-gpt-5-5",               "github_copilot", "gpt-5.5",                 "GPT-5.5",                "OpenAI flagship via Copilot",                                     ("smart",)),
    Model("gh-gpt-5-4",               "github_copilot", "gpt-5.4",                 "GPT-5.4",                "Previous flagship",                                               ("smart",)),
    Model("gh-gpt-5-4-mini",          "github_copilot", "gpt-5.4-mini",            "GPT-5.4 Mini",           "Lightweight GPT — fast and cheap",                                ("fast", "cheap")),
    Model("gh-gpt-5-3-codex",         "github_copilot", "gpt-5.3-codex",           "GPT-5.3 Codex",          "Coding-optimized OpenAI model",                                   ("coding",)),
    Model("gh-gpt-5-2",               "github_copilot", "gpt-5.2",                 "GPT-5.2",                "Older GPT-5 line",                                                ("balanced",)),
    Model("gh-gpt-4-1",               "github_copilot", "gpt-4.1",                 "GPT-4.1",                "Reliable workhorse",                                              ("balanced",)),
    Model("gh-grok-code-fast-1",      "github_copilot", "grok-code-fast-1",        "Grok Code Fast 1",       "xAI fast coding model via Copilot",                               ("fast", "coding")),
    Model("gh-gemini-3-1-pro-preview","github_copilot", "gemini-3.1-pro-preview",  "Gemini 3.1 Pro (Preview)","Google preview model via Copilot",                                ("preview", "smart")),
    Model("gh-gemini-2-5-pro",        "github_copilot", "gemini-2.5-pro",          "Gemini 2.5 Pro",         "Google production model via Copilot",                             ("smart", "long-context")),

    # ---------- OpenAI (native) ----------
    Model("oa-gpt-4o",        "openai", "gpt-4o",        "GPT-4o",       "Flagship multimodal",                ("smart",)),
    Model("oa-gpt-4o-mini",   "openai", "gpt-4o-mini",   "GPT-4o Mini",  "Fast + cheap",                       ("fast", "cheap")),
    Model("oa-o1-mini",       "openai", "o1-mini",       "o1 Mini",      "Reasoning-focused (slow, smart)",    ("reasoning",)),
    Model("oa-gpt-4-turbo",   "openai", "gpt-4-turbo",   "GPT-4 Turbo",  "128k context, solid all-rounder",    ("balanced", "long-context")),

    # ---------- Anthropic (native) ----------
    Model("an-sonnet-3-5",    "anthropic", "claude-3-5-sonnet-latest", "Claude 3.5 Sonnet", "Best price/perf",  ("balanced",)),
    Model("an-haiku-3-5",     "anthropic", "claude-3-5-haiku-latest",  "Claude 3.5 Haiku",  "Fast and cheap",   ("fast", "cheap")),
    Model("an-opus-3",        "anthropic", "claude-3-opus-latest",     "Claude 3 Opus",     "Heavy reasoning",  ("smart",)),

    # ---------- Google Gemini (native) ----------
    Model("gg-gemini-1-5-pro",   "google", "gemini-1.5-pro",   "Gemini 1.5 Pro",   "1M-token context flagship", ("smart", "long-context")),
    Model("gg-gemini-1-5-flash", "google", "gemini-1.5-flash", "Gemini 1.5 Flash", "Fast and cheap",            ("fast", "cheap")),

    # ---------- xAI Grok (native) ----------
    Model("xai-grok-2",       "xai", "grok-2-latest", "Grok 2",       "xAI flagship",       ("smart",)),
    Model("xai-grok-2-mini",  "xai", "grok-2-mini",   "Grok 2 Mini",  "Fast and cheap",     ("fast", "cheap")),

    # ---------- DeepSeek ----------
    Model("ds-chat",   "deepseek", "deepseek-chat",     "DeepSeek V3",  "General chat — very cheap",       ("cheap", "balanced")),
    Model("ds-r1",     "deepseek", "deepseek-reasoner", "DeepSeek R1",  "Reasoning model — chain-of-thought", ("reasoning",)),

    # ---------- OpenRouter (one provider, many models via api_name) ----------
    Model("or-auto",                "openrouter", "openrouter/auto",              "Auto-Router",          "Picks the best model for your prompt", ("auto",)),
    Model("or-claude-3-5-sonnet",   "openrouter", "anthropic/claude-3.5-sonnet",  "Claude 3.5 Sonnet",    "Via OpenRouter",                       ("balanced",)),
    Model("or-gpt-4o",              "openrouter", "openai/gpt-4o",                "GPT-4o",               "Via OpenRouter",                       ("smart",)),
    Model("or-llama-3-3-70b",       "openrouter", "meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B",   "Open weights — strong",                ("open",)),
    Model("or-mistral-large",       "openrouter", "mistralai/mistral-large",      "Mistral Large",        "European flagship",                    ("balanced",)),
    Model("or-deepseek-r1",         "openrouter", "deepseek/deepseek-r1",         "DeepSeek R1",          "Reasoning via OpenRouter",             ("reasoning",)),
    Model("or-qwen-2-5-72b",        "openrouter", "qwen/qwen-2.5-72b-instruct",   "Qwen 2.5 72B",         "Alibaba open model",                   ("open",)),
    Model("or-gemini-1-5-pro",      "openrouter", "google/gemini-pro-1.5",        "Gemini 1.5 Pro",       "Google via OpenRouter",                ("smart", "long-context")),
]


# Provider display order in the top-level menu.
PROVIDERS: list[tuple[str, str]] = [
    ("github_copilot", "🐙 GitHub Copilot Pro+"),
    ("openai",         "🟢 OpenAI"),
    ("anthropic",      "🟣 Anthropic"),
    ("google",         "🔵 Google Gemini"),
    ("xai",            "⚫ xAI Grok"),
    ("deepseek",       "🐋 DeepSeek"),
    ("openrouter",     "🌐 OpenRouter (100+)"),
]


ALL_MODELS: dict[str, Model] = {m.id: m for m in _CATALOG}


def models_for(provider_key: str) -> list[Model]:
    return [m for m in _CATALOG if m.provider == provider_key]


def get_model(model_id: str) -> Model | None:
    return ALL_MODELS.get(model_id)


def default_model_for(provider_key: str) -> str | None:
    ms = models_for(provider_key)
    return ms[0].id if ms else None


def provider_label(key: str) -> str:
    for k, label in PROVIDERS:
        if k == key:
            return label
    return key
