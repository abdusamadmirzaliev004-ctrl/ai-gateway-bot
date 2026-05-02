from __future__ import annotations
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings
from database.models import Base

log = logging.getLogger("database")

_settings = get_settings()
_url = _settings.database_url


def _validate_db_url(url: str) -> None:
    """Catch the classic Railway mistake: forgetting to wire the Postgres
    plugin's DATABASE_URL reference, or leaving the local dev value in place."""
    in_prod = bool(os.environ.get("RAILWAY_ENVIRONMENT")
                   or os.environ.get("WEBHOOK_URL")
                   or os.environ.get("RAILWAY_PROJECT_ID"))

    if in_prod and url.startswith("sqlite"):
        raise RuntimeError(
            "DATABASE_URL is set to SQLite in a production environment. "
            "Add Railway's Postgres plugin and reference its DATABASE_URL "
            "(prefix it with 'postgresql+asyncpg://')."
        )

    if "postgres" in url and ("localhost" in url or "127.0.0.1" in url):
        if in_prod:
            raise RuntimeError(
                "DATABASE_URL is pointing to localhost (127.0.0.1:5432) but "
                "we're running on Railway. Add the Postgres plugin to this "
                "project, then on the bot service set DATABASE_URL as a "
                "variable reference to the Postgres service's DATABASE_URL "
                "and rewrite the prefix to 'postgresql+asyncpg://'. "
                f"Current value: {url!r}"
            )
        log.warning("DATABASE_URL points to localhost — fine for local dev, "
                    "but will fail on Railway/Render/Fly.")

    if url.startswith("postgresql://") and "+asyncpg" not in url:
        raise RuntimeError(
            "DATABASE_URL uses the bare 'postgresql://' driver, but this app "
            "needs the async driver. Change the prefix to "
            "'postgresql+asyncpg://'. "
            f"Current value: {url.split('@')[-1] if '@' in url else url!r}"
        )


_validate_db_url(_url)
log.info("DB URL host: %s",
         _url.split("@")[-1].split("/")[0] if "@" in _url else "(local)")

engine = create_async_engine(_url, echo=False, pool_pre_ping=True)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
