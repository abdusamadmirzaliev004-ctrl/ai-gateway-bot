from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Message, DailyUsage
from config.settings import get_settings


async def get_or_create_user(session: AsyncSession, tg_user) -> User:
    user = await session.get(User, tg_user.id)
    s = get_settings()
    if user is None:
        user = User(
            id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            provider=s.default_provider,
            mode=s.default_mode,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        user.last_active = datetime.utcnow()
        await session.commit()
    return user


async def update_user(session: AsyncSession, user: User, **fields) -> User:
    for k, v in fields.items():
        setattr(user, k, v)
    await session.commit()
    await session.refresh(user)
    return user


async def set_user_model(session: AsyncSession, user: User, provider: str, model_id: str) -> User:
    """Switch active model and remember it for this provider."""
    user.provider = provider
    user.model_id = model_id
    lm = dict(user.last_models or {})
    lm[provider] = model_id
    user.last_models = lm
    await session.commit()
    await session.refresh(user)
    return user


async def select_provider(session: AsyncSession, user: User, provider: str) -> User:
    """Switch provider; restore last-used model for that provider if any."""
    from providers import default_model_for
    user.provider = provider
    last = (user.last_models or {}).get(provider)
    user.model_id = last or default_model_for(provider)
    await session.commit()
    await session.refresh(user)
    return user


async def add_message(session: AsyncSession, user_id: int, role: str, content: str,
                      provider: str | None = None, model: str | None = None, tokens: int = 0) -> Message:
    msg = Message(user_id=user_id, role=role, content=content,
                  provider=provider, model=model, tokens=tokens)
    session.add(msg)
    await session.commit()
    return msg


async def get_history(session: AsyncSession, user_id: int, limit: int = 12) -> list[Message]:
    q = (select(Message).where(Message.user_id == user_id)
         .order_by(Message.id.desc()).limit(limit))
    rows = (await session.execute(q)).scalars().all()
    return list(reversed(rows))


async def clear_history(session: AsyncSession, user_id: int) -> int:
    msgs = (await session.execute(select(Message).where(Message.user_id == user_id))).scalars().all()
    for m in msgs:
        await session.delete(m)
    await session.commit()
    return len(msgs)


async def pop_last_assistant(session: AsyncSession, user_id: int) -> Message | None:
    q = (select(Message).where(Message.user_id == user_id, Message.role == "assistant")
         .order_by(Message.id.desc()).limit(1))
    msg = (await session.execute(q)).scalar_one_or_none()
    if msg:
        await session.delete(msg)
        await session.commit()
    return msg


async def get_today_usage(session: AsyncSession, user_id: int) -> DailyUsage:
    today = date.today()
    q = select(DailyUsage).where(DailyUsage.user_id == user_id, DailyUsage.day == today)
    row = (await session.execute(q)).scalar_one_or_none()
    if row is None:
        row = DailyUsage(user_id=user_id, day=today, messages=0, tokens=0)
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def bump_usage(session: AsyncSession, user_id: int, messages: int = 0, tokens: int = 0) -> DailyUsage:
    usage = await get_today_usage(session, user_id)
    usage.messages += messages
    usage.tokens += tokens
    await session.commit()
    await session.refresh(usage)
    return usage


# --- Admin helpers ---
async def list_users(session: AsyncSession, limit: int = 25) -> list[User]:
    q = select(User).order_by(User.last_active.desc()).limit(limit)
    return list((await session.execute(q)).scalars().all())


async def total_stats(session: AsyncSession) -> dict:
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    total_msgs = (await session.execute(select(func.count(Message.id)))).scalar() or 0
    total_tokens = (await session.execute(select(func.coalesce(func.sum(Message.tokens), 0)))).scalar() or 0
    banned = (await session.execute(select(func.count(User.id)).where(User.is_banned == True))).scalar() or 0  # noqa: E712
    return {"users": total_users, "messages": total_msgs, "tokens": int(total_tokens), "banned": banned}


async def find_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)
