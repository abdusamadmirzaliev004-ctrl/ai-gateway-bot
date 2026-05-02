from __future__ import annotations
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.db import SessionLocal
from services import repo
from config.settings import get_settings

router = Router()


def _is_admin(uid: int) -> bool:
    return uid in get_settings().admin_ids


def _admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Stats", callback_data="adm:stats")
    kb.button(text="👥 Users", callback_data="adm:users")
    kb.adjust(2)
    return kb.as_markup()


@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("<b>Admin Panel</b>\n"
                         "Commands:\n"
                         "/stats — totals\n"
                         "/users — recent users\n"
                         "/ban &lt;user_id&gt;\n"
                         "/unban &lt;user_id&gt;\n"
                         "/setlimit &lt;user_id&gt; &lt;msgs&gt; &lt;tokens&gt;",
                         reply_markup=_admin_menu(), parse_mode="HTML")


@router.message(Command("stats"))
@router.callback_query(F.data == "adm:stats")
async def stats(event):
    user = event.from_user
    if not _is_admin(user.id):
        return
    async with SessionLocal() as s:
        st = await repo.total_stats(s)
    text = ("<b>Stats</b>\n"
            f"Users: <b>{st['users']}</b> (banned: {st['banned']})\n"
            f"Messages: <b>{st['messages']}</b>\n"
            f"Tokens: <b>{st['tokens']}</b>")
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=_admin_menu(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(Command("users"))
@router.callback_query(F.data == "adm:users")
async def users(event):
    user = event.from_user
    if not _is_admin(user.id):
        return
    async with SessionLocal() as s:
        rows = await repo.list_users(s, limit=20)
    lines = ["<b>Recent users</b>"]
    for u in rows:
        flag = "🚫" if u.is_banned else "✅"
        uname = f"@{u.username}" if u.username else (u.first_name or "—")
        lines.append(f"{flag} <code>{u.id}</code> {escape(uname)} · {escape(u.provider)}")
    text = "\n".join(lines) if rows else "No users yet."
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=_admin_menu(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(Command("ban"))
async def ban_cmd(message: Message):
    if not _is_admin(message.from_user.id): return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /ban &lt;user_id&gt;", parse_mode="HTML"); return
    uid = int(parts[1])
    async with SessionLocal() as s:
        u = await repo.find_user(s, uid)
        if not u: await message.answer("No such user."); return
        await repo.update_user(s, u, is_banned=True)
    await message.answer(f"Banned {uid}.")


@router.message(Command("unban"))
async def unban_cmd(message: Message):
    if not _is_admin(message.from_user.id): return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /unban &lt;user_id&gt;", parse_mode="HTML"); return
    uid = int(parts[1])
    async with SessionLocal() as s:
        u = await repo.find_user(s, uid)
        if not u: await message.answer("No such user."); return
        await repo.update_user(s, u, is_banned=False)
    await message.answer(f"Unbanned {uid}.")


@router.message(Command("setlimit"))
async def setlimit_cmd(message: Message):
    if not _is_admin(message.from_user.id): return
    parts = (message.text or "").split()
    if len(parts) != 4 or not all(p.lstrip("-").isdigit() for p in parts[1:]):
        await message.answer("Usage: /setlimit &lt;user_id&gt; &lt;msgs&gt; &lt;tokens&gt;", parse_mode="HTML"); return
    uid, msgs, toks = int(parts[1]), int(parts[2]), int(parts[3])
    async with SessionLocal() as s:
        u = await repo.find_user(s, uid)
        if not u: await message.answer("No such user."); return
        await repo.update_user(s, u, daily_message_limit=msgs, daily_token_limit=toks)
    await message.answer(f"Limits for {uid}: {msgs} msgs / {toks} tokens.")
