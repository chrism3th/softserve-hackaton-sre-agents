"""BaseAction: the contract every action must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.events import DomainEvent


class BaseAction(ABC):
    """A single, self-contained reaction to a domain event.

    Actions should be stateless.  Any shared state (DB sessions, HTTP
    clients) must be created inside ``execute`` or injected via the
    constructor before registration.
    """

    @abstractmethod
    async def execute(self, event: DomainEvent) -> None:
        """React to *event*.  Must not raise — log and swallow errors."""
