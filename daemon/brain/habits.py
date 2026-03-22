"""Brain habits — pattern detection from recurring events."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Habit:
    category: str
    pattern: str
    hour: int
    occurrences: int
    confidence: float


class HabitTracker:
    """Detects recurring patterns by category, pattern and hour."""

    def __init__(self, min_occurrences: int = 3) -> None:
        self.min_occurrences = min_occurrences
        # _records[category][hour][pattern] = count
        self._records: dict[str, dict[int, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

    def record(self, category: str, pattern: str, hour: Optional[int] = None) -> None:
        if hour is None:
            hour = datetime.now(timezone.utc).hour
        self._records[category][hour][pattern] += 1

    def detect(self) -> list[Habit]:
        habits: list[Habit] = []
        for category, by_hour in self._records.items():
            for hour, by_pattern in by_hour.items():
                for pattern, count in by_pattern.items():
                    if count >= self.min_occurrences:
                        confidence = min(1.0, count / (self.min_occurrences * 2))
                        habits.append(Habit(
                            category=category,
                            pattern=pattern,
                            hour=hour,
                            occurrences=count,
                            confidence=confidence,
                        ))
        habits.sort(key=lambda h: h.occurrences, reverse=True)
        return habits

    def predict(self, hour: int) -> list[Habit]:
        habits: list[Habit] = []
        for category, by_hour in self._records.items():
            if hour not in by_hour:
                continue
            for pattern, count in by_hour[hour].items():
                if count >= self.min_occurrences:
                    confidence = min(1.0, count / (self.min_occurrences * 2))
                    habits.append(Habit(
                        category=category,
                        pattern=pattern,
                        hour=hour,
                        occurrences=count,
                        confidence=confidence,
                    ))
        habits.sort(key=lambda h: h.occurrences, reverse=True)
        return habits

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Convert nested defaultdicts to plain dicts for JSON serialization
        data = {
            "min_occurrences": self.min_occurrences,
            "records": {
                cat: {str(h): dict(patterns) for h, patterns in by_hour.items()}
                for cat, by_hour in self._records.items()
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> HabitTracker:
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        tracker = cls(min_occurrences=data["min_occurrences"])
        for cat, by_hour in data["records"].items():
            for hour_str, patterns in by_hour.items():
                for pattern, count in patterns.items():
                    tracker._records[cat][int(hour_str)][pattern] = count
        return tracker
