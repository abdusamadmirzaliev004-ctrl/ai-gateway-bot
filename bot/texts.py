from __future__ import annotations
from html import escape


WELCOME = (
    "<b>AI Gateway</b>\n"
    "One bot. Many AI minds.\n\n"
    "Pick an option below to get started."
)

HELP = (
    "<b>Help</b>\n\n"
    "• <b>Chat</b> — send any message and the selected model replies.\n"
    "• <b>Choose Model</b> — pick a provider, then a specific model.\n"
    "• <b>Mode</b> — Fast / Smart / Creative (controls temperature + token budget).\n"
    "• <b>Style</b> — Short or Detailed answers.\n"
    "• <b>Memory</b> — toggle conversation context.\n"
    "• <b>Regenerate</b> — re-roll the last assistant reply.\n"
    "• <b>Clear</b> — wipe your conversation history.\n\n"
    "Daily quotas reset at 00:00 UTC."
)


def _model_label(user) -> str:
    from providers import get_model
    if user.model_id:
        m = get_model(user.model_id)
        if m:
            return m.label
    return "(default)"


def usage_text(user, usage, msg_limit, tok_limit) -> str:
    return (
        "<b>Usage today</b>\n"
        f"Messages: <b>{usage.messages}</b> / {msg_limit}\n"
        f"Tokens:   <b>{usage.tokens}</b> / {tok_limit}\n\n"
        f"Provider: <b>{escape(user.provider)}</b>\n"
        f"Model: <b>{escape(_model_label(user))}</b>\n"
        f"Mode: <b>{escape(user.mode)}</b>  ·  Style: <b>{escape(user.style)}</b>\n"
        f"Memory: <b>{'on' if user.memory_enabled else 'off'}</b>"
    )


def home_text(user) -> str:
    return (
        f"{WELCOME}\n\n"
        f"<i>Current:</i> <b>{escape(_model_label(user))}</b>"
        f"  ·  {escape(user.mode)}  ·  {escape(user.style)}"
    )


def model_picker_intro(provider_key: str) -> str:
    from providers import provider_label, models_for
    label = provider_label(provider_key)
    n = len(models_for(provider_key))
    return f"<b>{escape(label)}</b>\n{n} model(s) available — tap to select."


def provider_picker_intro() -> str:
    return "<b>Choose a provider</b>\nThen pick a specific model."
