"""ActionRegistry: maps event types to the actions that handle them.

Usage
-----
Register an action with the decorator::

    from app.actions.registry import action_registry
    from app.actions.base import BaseAction
    from app.domain.events import DomainEvent

    @action_registry.on("issue.status_changed")
    class MyAction(BaseAction):
        async def execute(self, event: DomainEvent) -> None:
            ...

The decorator registers a *single shared instance* of the class.
Actions must therefore be stateless (no mutable instance variables).

To add a new action, create it anywhere that is imported at startup
(e.g., ``actions/handlers/``) and make sure the module is imported in
``actions/handlers/__init__.py``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from app.actions.base import BaseAction


class ActionRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[BaseAction]] = defaultdict(list)

    def on(self, event_type: str) -> Callable[[type[BaseAction]], type[BaseAction]]:
        """Class decorator — registers one instance of the decorated class."""

        def decorator(cls: type[BaseAction]) -> type[BaseAction]:
            self._handlers[event_type].append(cls())
            return cls

        return decorator

    def get_handlers(self, event_type: str) -> list[BaseAction]:
        """Return all handlers registered for *event_type* (may be empty)."""
        return list(self._handlers.get(event_type, []))

    def registered_event_types(self) -> list[str]:
        """Return all event types that have at least one handler."""
        return sorted(self._handlers)


action_registry = ActionRegistry()
