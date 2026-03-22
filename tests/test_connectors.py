"""Tests for Gmail and Calendar connectors."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from daemon.connectors import GmailConnector, Email, CalendarConnector, Meeting


def test_email_creation():
    e = Email(sender="alice@example.com", subject="Hello", snippet="Hi there")
    assert e.sender == "alice@example.com"
    assert e.subject == "Hello"
    assert e.unread is True
    assert e.labels == []


def test_gmail_connector_creation():
    gc = GmailConnector()
    assert gc.name == "gmail"
    assert gc.enabled is False


def test_gmail_format_summary():
    gc = GmailConnector()
    emails = [
        Email(sender="bob@example.com", subject="Meeting notes"),
        Email(sender="carol@example.com", subject="Invoice"),
    ]
    summary = gc.format_summary(emails)
    assert "bob@example.com" in summary
    assert "Meeting notes" in summary
    assert "carol@example.com" in summary
    assert "Invoice" in summary


def test_meeting_creation():
    m = Meeting(
        title="Standup",
        start="2026-03-22T09:00:00",
        end="2026-03-22T09:30:00",
        location="Room A",
    )
    assert m.title == "Standup"
    assert m.duration_min == 30
    assert m.start_dt == datetime(2026, 3, 22, 9, 0)


def test_calendar_connector():
    cc = CalendarConnector()
    assert cc.name == "calendar"
    assert cc.enabled is False


def test_calendar_upcoming_summary():
    cc = CalendarConnector()
    meetings = [
        Meeting(title="Standup", start="2026-03-22T09:00:00", end="2026-03-22T09:30:00"),
        Meeting(title="Review", start="2026-03-22T14:00:00", end="2026-03-22T15:00:00", location="Zoom"),
    ]
    summary = cc.format_summary(meetings)
    assert "2 meeting(s) today" in summary
    assert "Standup" in summary
    assert "Review" in summary
    assert "Zoom" in summary


def test_calendar_next_meeting():
    cc = CalendarConnector()
    now = datetime.now()
    past = (now - timedelta(hours=2)).isoformat()
    past_end = (now - timedelta(hours=1)).isoformat()
    future = (now + timedelta(hours=1)).isoformat()
    future_end = (now + timedelta(hours=2)).isoformat()

    meetings = [
        Meeting(title="Done", start=past, end=past_end),
        Meeting(title="Next", start=future, end=future_end),
    ]
    result = cc.next_meeting(meetings)
    assert result is not None
    assert result.title == "Next"

    # All past — should return None
    assert cc.next_meeting([meetings[0]]) is None
