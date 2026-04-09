"""Async database engine and session factory.

Single-engine, app-wide. Use ``get_session`` as a FastAPI dependency or
``session_scope`` as a context manager from background code.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a transactional session per request.

    Commits on clean exit; rolls back automatically on exception.
    """
    async with get_sessionmaker().begin() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Context-manager variant for use outside request handlers.

    Commits on clean exit; rolls back automatically on exception.
    Callers should NOT call session.commit() themselves.
    """
    async with get_sessionmaker().begin() as session:
        yield session
