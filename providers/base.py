from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class GenerationSettings:
    mode: str = "fast"          # fast | smart | creative
    style: str = "short"        # short | detailed
    max_tokens: int | None = None
    temperature: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    text: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ProviderError(Exception):
    """Raised by providers on any failure (network, auth, rate limit, etc)."""


class BaseProvider(ABC):
    name: str = "base"
    # Map mode -> default model
    model_map: dict[str, str] = {}

    def resolve_model(self, mode: str, override: str | None = None) -> str:
        if override:
            return override
        return self.model_map.get(mode) or next(iter(self.model_map.values()))

    def system_prompt(self, settings: GenerationSettings) -> str:
        if settings.style == "detailed":
            return "You are a helpful AI assistant. Provide thorough, well-structured answers with examples when useful."
        return "You are a helpful AI assistant. Be concise and direct. Prefer short answers unless asked otherwise."

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        settings: GenerationSettings,
        model: str | None = None,
    ) -> GenerationResult: ...
