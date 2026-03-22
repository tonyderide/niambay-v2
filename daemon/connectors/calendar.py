"""Google Calendar connector — MCP-ready stub."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class Meeting:
    title: str
    start: str  # ISO format
    end: str    # ISO format
    location: str = ""
    description: str = ""
    attendees: List[str] = field(default_factory=list)

    @property
    def start_dt(self) -> datetime:
        return datetime.fromisoformat(self.start)

    @property
    def end_dt(self) -> datetime:
        return datetime.fromisoformat(self.end)

    @property
    def duration_min(self) -> int:
        delta = self.end_dt - self.start_dt
        return int(delta.total_seconds() / 60)


class CalendarConnector:
    name = "calendar"

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
        self._service = None

    @property
    def enabled(self) -> bool:
        return self._service is not None

    def fetch_today(self) -> List[Meeting]:
        """Fetch today's meetings. Stub — returns empty list until wired to API."""
        return []

    def next_meeting(self, meetings: List[Meeting]) -> Optional[Meeting]:
        """Return the next upcoming meeting (skip past ones)."""
        now = datetime.now()
        future = [m for m in meetings if m.start_dt > now]
        if not future:
            return None
        return min(future, key=lambda m: m.start_dt)

    def format_summary(self, meetings: List[Meeting]) -> str:
        """Format a human-readable summary of meetings."""
        if not meetings:
            return "No meetings today."
        lines = [f"{len(meetings)} meeting(s) today:"]
        for m in meetings:
            t = m.start_dt.strftime("%H:%M")
            loc = f" @ {m.location}" if m.location else ""
            lines.append(f"  - {t} {m.title} ({m.duration_min}min){loc}")
        return "\n".join(lines)
