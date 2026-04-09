"""EventDispatcher: fan out a domain event to all registered handlers.

Deliberately has no dependency on FastAPI — callers decide whether to
schedule dispatch as a background task or await it directly.

Typical usage from a webhook route::

    background_tasks.add_task(event_dispatcher.dispatch, event)
"""

from __future__ import annotations

from app.actions.registry import action_registry
from app.core.logging import get_logger
from app.domain.events import DomainEvent

logger = get_logger(__name__)


class EventDispatcher:
    async def dispatch(self, event: DomainEvent) -> None:
        """Run all handlers registered for *event.event_type*.

        Errors inside individual handlers are caught and logged so one
        failing handler never blocks the others.
        """
        handlers = action_registry.get_handlers(event.event_type)
        if not handlers:
            logger.debug(
                "event_dispatcher.no_handlers",
                event_type=event.event_type,
                issue=event.issue_identifier,
            )
            return

        logger.info(
            "event_dispatcher.dispatching",
            event_type=event.event_type,
            issue=event.issue_identifier,
            handler_count=len(handlers),
        )

        for handler in handlers:
            try:
                logger.debug(
                    "event_dispatcher.handler_start",
                    handler=handler.__class__.__name__,
                )
                await handler.execute(event)
                logger.debug(
                    "event_dispatcher.handler_done",
                    handler=handler.__class__.__name__,
                )
            except Exception:
                logger.exception(
                    "event_dispatcher.handler_error",
                    handler=handler.__class__.__name__,
                    event_type=event.event_type,
                )


event_dispatcher = EventDispatcher()
