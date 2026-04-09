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
        """Persist a new row and commit."""
        instance: ModelT = self._model(**kwargs)
        session.add(instance)
        await session.commit()
        return instance
