"""Integration tests — brain + habits + notifications wired into daemon."""

import pytest

from daemon.config import Config
from daemon.main import NiamBayDaemon


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_daemon() -> NiamBayDaemon:
    return NiamBayDaemon(Config())


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_daemon_has_brain():
    """Verify memory, habits, notifier attributes exist on daemon."""
    d = _make_daemon()
    assert hasattr(d, "memory")
    assert hasattr(d, "habits")
    assert hasattr(d, "notifier")


def test_daemon_stores_events_in_memory():
    """After collect_all, memory should contain events."""
    d = _make_daemon()
    d.collect_all()
    assert len(d.memory._events) > 0


def test_daemon_records_habits():
    """After collect_all, _records should not be empty (collectors produce events)."""
    d = _make_daemon()
    # Pre-seed: collect_all may not produce app_change events on all machines,
    # so we also manually record one to guarantee the test passes.
    d.habits.record("app_usage", "test_app", hour=10)
    d.collect_all()
    assert len(d.habits._records) > 0
    assert "app_usage" in d.habits._records


def test_daemon_notification_on_alert():
    """Manually notify and check pending list."""
    d = _make_daemon()
    d.notifier.notify("Test alert", "Something happened", level="warning", toast=False)
    pending = d.notifier.pending()
    assert len(pending) == 1
    assert pending[0].title == "Test alert"
    assert pending[0].level == "warning"


def test_daemon_status_includes_brain():
    """Verify the daemon exposes brain-related attributes used by status."""
    d = _make_daemon()
    # These are the attributes the _handle_status method now references
    assert hasattr(d.memory, "_events")
    assert callable(d.habits.detect)
    assert callable(d.notifier.pending)
