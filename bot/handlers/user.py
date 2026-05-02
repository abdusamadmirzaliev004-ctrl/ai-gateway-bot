from __future__ import annotations
import asyncio
import logging
from html import escape
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from database.db import SessionLocal
from services import repo
from services.limits import check_quota
from providers import (
    generate_response, AVAILABLE_PROVIDERS, get_model, models_for, default_model_for,
)
from providers.base import ChatMessage, GenerationSettings, ProviderError
from config.settings import get_settings
from bot import keyboards as kb
from bot import texts

router = Router()
log = logging.getLogger("bot")


# ---------- /start, /menu ----------
@router.message(CommandStart())
@router.message(Command("menu"))
async def start_cmd(message: Message):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, message.from_user)
    await message.answer(texts.home_text(user), reply_markup=kb.main_menu(), parse_mode="HTML")


@router.callback_query(F.data == "menu:home")
async def cb_home(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
    await cq.message.edit_text(texts.home_text(user), reply_markup=kb.main_menu(), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(cq: CallbackQuery):
    await cq.message.edit_text(texts.HELP, reply_markup=kb.back_button(), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data == "menu:chat")
async def cb_chat(cq: CallbackQuery):
    await cq.message.edit_text(
        "Send me any message and I'll reply.\n\nTip: use Settings to switch mode/style.",
        reply_markup=kb.back_button(),
        parse_mode="HTML",
    )
    await cq.answer()


# ---------- Provider / Model menu ----------
@router.callback_query(F.data == "menu:provider")
async def cb_prov_menu(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
    await cq.message.edit_text(
        texts.provider_picker_intro(),
        reply_markup=kb.provider_menu(user.provider),
        parse_mode="HTML",
    )
    await cq.answer()


@router.callback_query(F.data.startswith("prov:"))
async def cb_prov_pick(cq: CallbackQuery):
    name = cq.data.split(":", 1)[1]
    valid = {k for k, _ in AVAILABLE_PROVIDERS}
    if name not in valid:
        await cq.answer("Unknown provider", show_alert=True)
        return
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        # If user already on this provider, just show its models. Otherwise switch (and restore last model).
        if user.provider != name:
            user = await repo.select_provider(s, user, name)
    await cq.message.edit_text(
        texts.model_picker_intro(name),
        reply_markup=kb.model_menu(name, user.model_id),
        parse_mode="HTML",
    )
    await cq.answer()


@router.callback_query(F.data.startswith("mdl:"))
async def cb_model_pick(cq: CallbackQuery):
    model_id = cq.data.split(":", 1)[1]
    m = get_model(model_id)
    if not m:
        await cq.answer("Unknown model", show_alert=True); return
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        user = await repo.set_user_model(s, user, m.provider, m.id)
    await cq.message.edit_text(
        f"✅ <b>{escape(m.label)}</b> selected\n<i>{escape(m.description)}</i>",
        reply_markup=kb.model_menu(m.provider, m.id),
        parse_mode="HTML",
    )
    await cq.answer("Model switched")


# ---------- Settings ----------
@router.callback_query(F.data == "menu:settings")
async def cb_settings(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
    await cq.message.edit_text("<b>Settings</b>", reply_markup=kb.settings_menu(user), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data == "set:mode")
async def cb_set_mode(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
    await cq.message.edit_text("<b>Mode</b>", reply_markup=kb.mode_menu(user.mode), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("mode:"))
async def cb_pick_mode(cq: CallbackQuery):
    mode = cq.data.split(":", 1)[1]
    if mode not in {"fast", "smart", "creative"}:
        await cq.answer(); return
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        await repo.update_user(s, user, mode=mode)
    await cq.message.edit_text("<b>Mode</b>", reply_markup=kb.mode_menu(mode), parse_mode="HTML")
    await cq.answer(f"Mode: {mode}")


@router.callback_query(F.data == "set:style")
async def cb_set_style(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
    await cq.message.edit_text("<b>Style</b>", reply_markup=kb.style_menu(user.style), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("style:"))
async def cb_pick_style(cq: CallbackQuery):
    style = cq.data.split(":", 1)[1]
    if style not in {"short", "detailed"}:
        await cq.answer(); return
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        await repo.update_user(s, user, style=style)
    await cq.message.edit_text("<b>Style</b>", reply_markup=kb.style_menu(style), parse_mode="HTML")
    await cq.answer(f"Style: {style}")


@router.callback_query(F.data == "set:memory")
async def cb_toggle_memory(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        await repo.update_user(s, user, memory_enabled=not user.memory_enabled)
        u2 = user
    await cq.message.edit_text("<b>Settings</b>", reply_markup=kb.settings_menu(u2), parse_mode="HTML")
    await cq.answer(f"Memory: {'on' if u2.memory_enabled else 'off'}")


# ---------- Usage ----------
@router.callback_query(F.data == "menu:usage")
async def cb_usage(cq: CallbackQuery):
    s_ = get_settings()
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        usage = await repo.get_today_usage(s, user.id)
    await cq.message.edit_text(
        texts.usage_text(user, usage,
                         user.daily_message_limit or s_.daily_message_limit,
                         user.daily_token_limit or s_.daily_token_limit),
        reply_markup=kb.back_button(), parse_mode="HTML",
    )
    await cq.answer()


# ---------- Chat actions ----------
@router.callback_query(F.data == "chat:clear")
async def cb_clear(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        n = await repo.clear_history(s, user.id)
    await cq.answer(f"Cleared {n} messages", show_alert=False)


@router.callback_query(F.data == "chat:regen")
async def cb_regen(cq: CallbackQuery):
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, cq.from_user)
        # remove last assistant; keep last user prompt
        await repo.pop_last_assistant(s, user.id)
        history = await repo.get_history(s, user.id, limit=20)
    if not history or history[-1].role != "user":
        await cq.answer("Nothing to regenerate", show_alert=True); return
    last_user = history[-1].content
    await cq.answer("Regenerating…")
    await _do_chat(cq.message, cq.from_user, last_user, append_user=False)


# ---------- Free text -> chat ----------
@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message):
    await _do_chat(message, message.from_user, message.text or "")


async def _do_chat(reply_target: Message, tg_user, prompt: str, *, append_user: bool = True):
    s_ = get_settings()
    async with SessionLocal() as s:
        user = await repo.get_or_create_user(s, tg_user)
        gate = await check_quota(s, user)
        if not gate.ok:
            await reply_target.answer(f"⚠️ {gate.reason}", reply_markup=kb.back_button("menu:home"))
            return

        if append_user:
            await repo.add_message(s, user.id, "user", prompt)

        # Build context
        if user.memory_enabled:
            history = await repo.get_history(s, user.id, limit=12)
            messages = [ChatMessage(role=m.role, content=m.content) for m in history if m.role in ("user", "assistant")]
            if not messages or messages[-1].role != "user":
                messages.append(ChatMessage(role="user", content=prompt))
        else:
            messages = [ChatMessage(role="user", content=prompt)]

        provider = user.provider
        # Resolve catalog id -> api_name
        api_model = None
        if user.model_id:
            m = get_model(user.model_id)
            if m and m.provider == provider:
                api_model = m.api_name
        settings = GenerationSettings(mode=user.mode, style=user.style)

    # typing indicator (outside DB session)
    try:
        await reply_target.bot.send_chat_action(reply_target.chat.id, ChatAction.TYPING)
    except Exception:
        pass

    typing_task = asyncio.create_task(_keep_typing(reply_target))
    try:
        try:
            result = await generate_response(messages, provider=provider, model=api_model, settings=settings)
        except ProviderError as e:
            log.exception("Generation failed")
            await reply_target.answer(f"❌ All providers failed.\n<code>{escape(str(e))[:300]}</code>",
                                      reply_markup=kb.reply_actions(), parse_mode="HTML")
            return
    finally:
        typing_task.cancel()

    async with SessionLocal() as s:
        await repo.add_message(s, tg_user.id, "assistant", result.text,
                               provider=result.provider, model=result.model,
                               tokens=result.total_tokens)
        await repo.bump_usage(s, tg_user.id, messages=1, tokens=result.total_tokens)

    footer = f"\n\n<i>— {escape(result.provider)} · {escape(result.model)} · {result.total_tokens} tok</i>"
    text = (result.text or "(empty response)") + footer
    # Telegram message cap is 4096 chars
    if len(text) > 4000:
        text = text[:3990] + "…"
    await reply_target.answer(text, reply_markup=kb.reply_actions(), parse_mode="HTML")


async def _keep_typing(message: Message):
    try:
        while True:
            await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
