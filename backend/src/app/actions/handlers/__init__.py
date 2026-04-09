"""Concrete action handlers.

Import every handler module here so the registry decorators run at
startup when this package is imported.
"""

from app.actions.handlers import issue_handlers as issue_handlers
from app.actions.handlers import notify_reporter as notify_reporter
