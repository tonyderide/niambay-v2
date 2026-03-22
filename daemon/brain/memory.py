"""Brain memory — persistent event storage for the daemon."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class MemoryEvent:
    source: str
    event_type: str
    data: dict
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Memory:
    """Append-only event store with query, save and load."""

    def __init__(self, max_events: int = 10000) -> None:
        self.max_events = max_events
        self._events: list[MemoryEvent] = []

    # -- mutate --

    def store(self, event: MemoryEvent) -> None:
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]

    # -- query --

    def recent(self, n: int = 10) -> list[MemoryEvent]:
        return list(reversed(self._events[-n:]))

    def query(
        self,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[str] = None,
    ) -> list[MemoryEvent]:
        results = self._events
        if source is not None:
            results = [e for e in results if e.source == source]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if since is not None:
            results = [e for e in results if e.timestamp >= since]
        return results

    # -- persistence --

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self._events], f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str | Path, max_events: int = 10000) -> Memory:
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        mem = cls(max_events=max_events)
        mem._events = [MemoryEvent(**item) for item in raw]
        return mem
