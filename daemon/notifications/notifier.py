"""Notification system with optional Windows toast support."""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Graceful import of win10toast
try:
    from win10toast import ToastNotifier

    _toaster: Optional[ToastNotifier] = ToastNotifier()
except ImportError:
    _toaster = None

Level = Literal["info", "warning", "alert"]


@dataclass
class Notification:
    title: str
    message: str
    level: Level = "info"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class NotificationManager:
    """Manages a bounded queue of notifications with optional toast popups."""

    def __init__(self, max_notifications: int = 100) -> None:
        self._notifications: deque[Notification] = deque(maxlen=max_notifications)
        self._max = max_notifications

    # -- public API ----------------------------------------------------------

    def notify(
        self,
        title: str,
        message: str,
        level: Level = "info",
        toast: bool = True,
    ) -> Notification:
        """Create a notification, log it, and optionally show a Windows toast."""
        notif = Notification(title=title, message=message, level=level)
        self._notifications.append(notif)
        logger.info("notification [%s] %s: %s", level, title, message)

        if toast and level in ("warning", "alert") and _toaster is not None:
            try:
                _toaster.show_toast(
                    title,
                    message,
                    duration=5,
                    threaded=True,
                )
            except Exception:
                logger.debug("toast failed", exc_info=True)

        return notif

    def pending(self, level: Optional[Level] = None) -> list[Notification]:
        """Return unread notifications, optionally filtered by level."""
        return [
            n
            for n in self._notifications
            if not n.read and (level is None or n.level == level)
        ]

    def all(self) -> list[Notification]:
        """Return all notifications (read and unread)."""
        return list(self._notifications)

    def mark_read(self, notif_id: str) -> bool:
        """Mark a notification as read. Returns True if found."""
        for n in self._notifications:
            if n.id == notif_id:
                n.read = True
                return True
        return False
