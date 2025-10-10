from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    # Normalize to async driver for Postgres if a sync URL is provided
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


ENGINE = create_async_engine(get_database_url(), future=True, pool_pre_ping=True)
ASYNC_SESSION_MAKER = async_sessionmaker(ENGINE, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with ASYNC_SESSION_MAKER() as session:
        yield session


