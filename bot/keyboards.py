from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from providers import AVAILABLE_PROVIDERS, MODES, STYLES, models_for, get_model, provider_label


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💬  Chat with AI", callback_data="menu:chat")
    kb.button(text="🤖  Choose Model", callback_data="menu:provider")
    kb.button(text="📊  Usage / Limits", callback_data="menu:usage")
    kb.button(text="⚙️  Settings", callback_data="menu:settings")
    kb.button(text="❓  Help", callback_data="menu:help")
    kb.adjust(1)
    return kb.as_markup()


def back_button(target: str = "menu:home") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="‹ Back", callback_data=target)
    return kb.as_markup()


def provider_menu(current_provider: str) -> InlineKeyboardMarkup:
    """Top-level: list providers (grouped UI). Tap one to see its models."""
    kb = InlineKeyboardBuilder()
    for key, label in AVAILABLE_PROVIDERS:
        n = len(models_for(key))
        mark = "● " if key == current_provider else "○ "
        kb.button(text=f"{mark}{label}  ({n})", callback_data=f"prov:{key}")
    kb.button(text="‹ Back", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def _tags_str(tags: list[str]) -> str:
    return " · ".join(tags) if tags else ""


def model_menu(provider_key: str, current_model_id: str | None) -> InlineKeyboardMarkup:
    """List all models for a provider with tags, paginated implicitly by Telegram (long lists ok)."""
    kb = InlineKeyboardBuilder()
    for m in models_for(provider_key):
        mark = "● " if m.id == current_model_id else "○ "
        tag = _tags_str(m.tags)
        line = f"{mark}{m.label}" + (f"  ·  {tag}" if tag else "")
        kb.button(text=line, callback_data=f"mdl:{m.id}")
    kb.button(text="‹ Providers", callback_data="menu:provider")
    kb.adjust(1)
    return kb.as_markup()


def settings_menu(user) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"Mode: {user.mode}", callback_data="set:mode")
    kb.button(text=f"Style: {user.style}", callback_data="set:style")
    kb.button(text=f"Memory: {'on' if user.memory_enabled else 'off'}", callback_data="set:memory")
    kb.button(text="🧹  Clear chat", callback_data="chat:clear")
    kb.button(text="‹ Back", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def mode_menu(current: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in MODES:
        mark = "● " if key == current else "○ "
        kb.button(text=mark + label, callback_data=f"mode:{key}")
    kb.button(text="‹ Back", callback_data="menu:settings")
    kb.adjust(1)
    return kb.as_markup()


def style_menu(current: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in STYLES:
        mark = "● " if key == current else "○ "
        kb.button(text=mark + label, callback_data=f"style:{key}")
    kb.button(text="‹ Back", callback_data="menu:settings")
    kb.adjust(1)
    return kb.as_markup()


def reply_actions() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔁 Regenerate", callback_data="chat:regen")
    kb.button(text="🧹 Clear", callback_data="chat:clear")
    kb.button(text="🤖 Model", callback_data="menu:provider")
    kb.button(text="☰ Menu", callback_data="menu:home")
    kb.adjust(2, 2)
    return kb.as_markup()
