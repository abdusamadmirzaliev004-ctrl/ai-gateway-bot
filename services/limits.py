from __future__ import annotations
import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from services import repo
from config.settings import get_settings


@dataclass
class QuotaCheck:
    ok: bool
    reason: str = ""


class RateLimiter:
    """In-memory sliding-window rate limiter (per-user, per-minute)."""

    def __init__(self) -> None:
        self._hits: dict[int, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, user_id: int, limit_per_min: int) -> bool:
        now = time.time()
        async with self._lock:
            dq = self._hits[user_id]
            while dq and now - dq[0] > 60:
                dq.popleft()
            if len(dq) >= limit_per_min:
                return False
            dq.append(now)
            return True


rate_limiter = RateLimiter()


async def check_quota(session: AsyncSession, user: User) -> QuotaCheck:
    s = get_settings()
    if user.is_banned:
        return QuotaCheck(False, "You are banned from using this bot.")

    if not await rate_limiter.check(user.id, s.rate_limit_per_minute):
        return QuotaCheck(False, f"Rate limit: max {s.rate_limit_per_minute} messages/minute. Slow down a bit.")

    usage = await repo.get_today_usage(session, user.id)
    msg_limit = user.daily_message_limit or s.daily_message_limit
    tok_limit = user.daily_token_limit or s.daily_token_limit
    if usage.messages >= msg_limit:
        return QuotaCheck(False, f"Daily message limit reached ({msg_limit}). Resets at 00:00 UTC.")
    if usage.tokens >= tok_limit:
        return QuotaCheck(False, f"Daily token limit reached ({tok_limit}). Resets at 00:00 UTC.")
    return QuotaCheck(True)
