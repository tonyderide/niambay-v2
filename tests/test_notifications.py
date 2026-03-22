"""Tests for the notification manager."""

from daemon.notifications import Notification, NotificationManager


def test_notification_creation():
    n = Notification(title="Hello", message="World")
    assert n.title == "Hello"
    assert n.message == "World"
    assert n.level == "info"
    assert n.read is False
    assert len(n.id) == 8
    assert n.timestamp is not None


def test_manager_add_notification():
    mgr = NotificationManager()
    notif = mgr.notify("Test", "A message", toast=False)
    assert notif in mgr.all()
    assert len(mgr.all()) == 1


def test_manager_levels():
    mgr = NotificationManager()
    mgr.notify("Info", "info msg", level="info", toast=False)
    mgr.notify("Warn", "warn msg", level="warning", toast=False)
    mgr.notify("Alert", "alert msg", level="alert", toast=False)

    assert len(mgr.pending()) == 3
    assert len(mgr.pending(level="warning")) == 1
    assert mgr.pending(level="warning")[0].title == "Warn"
    assert len(mgr.pending(level="alert")) == 1


def test_manager_mark_read():
    mgr = NotificationManager()
    n = mgr.notify("X", "y", toast=False)
    assert len(mgr.pending()) == 1

    found = mgr.mark_read(n.id)
    assert found is True
    assert len(mgr.pending()) == 0
    assert mgr.mark_read("nonexistent") is False


def test_manager_max_notifications():
    mgr = NotificationManager(max_notifications=5)
    for i in range(10):
        mgr.notify(f"N{i}", f"msg{i}", toast=False)

    assert len(mgr.all()) == 5
    # oldest should have been evicted; newest kept
    titles = [n.title for n in mgr.all()]
    assert titles == ["N5", "N6", "N7", "N8", "N9"]
