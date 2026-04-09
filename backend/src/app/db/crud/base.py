"""Generic CRUD base class.

Provides a reusable ``create`` operation that any entity-specific CRUD
class can inherit. Keep business logic out of here.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUDBase(Generic[ModelT]):
    def __init__(self, model: type[ModelT]) -> None:
        self._model = model

    async def create(self, session: AsyncSession, **kwargs: Any) -> ModelT:
        """Stage a new row, flush to DB, and refresh server-generated fields.

        Does NOT commit. The caller (or the session context manager) owns the
        transaction boundary, which allows multiple writes to be composed into
        a single atomic transaction.
        """
        instance: ModelT = self._model(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance
