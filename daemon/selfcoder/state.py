"""SelfCoder state persistence — tracks task outcomes across cycles."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


@dataclass
class SelfCoderState:
    tasks_completed: List[str] = field(default_factory=list)
    tasks_failed: Dict[str, int] = field(default_factory=dict)
    tasks_skipped: List[str] = field(default_factory=list)
    total_lines_written: int = 0
    total_cycles: int = 0
    last_run: str = ""
    max_attempts: int = 2

    def __init__(self, max_attempts: int = 2):
        self.tasks_completed = []
        self.tasks_failed = {}
        self.tasks_skipped = []
        self.total_lines_written = 0
        self.total_cycles = 0
        self.last_run = ""
        self.max_attempts = max_attempts

    def record_success(self, task_name: str, branch: str, lines_changed: int) -> None:
        """Record a successful task completion."""
        self.tasks_completed.append(task_name)
        self.total_lines_written += lines_changed
        self.total_cycles += 1
        self.last_run = datetime.now(timezone.utc).isoformat()

    def record_failure(self, task_name: str, error: str) -> None:
        """Record a task failure, incrementing its attempt count."""
        self.tasks_failed[task_name] = self.tasks_failed.get(task_name, 0) + 1
        if self.should_skip(task_name) and task_name not in self.tasks_skipped:
            self.tasks_skipped.append(task_name)
        self.last_run = datetime.now(timezone.utc).isoformat()

    def should_skip(self, task_name: str) -> bool:
        """Return True if task has reached max attempts."""
        return self.tasks_failed.get(task_name, 0) >= self.max_attempts

    def save(self, path: str) -> None:
        """Persist state to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_skipped": self.tasks_skipped,
            "total_lines_written": self.total_lines_written,
            "total_cycles": self.total_cycles,
            "last_run": self.last_run,
            "max_attempts": self.max_attempts,
        }
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "SelfCoderState":
        """Load state from a JSON file."""
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        state = cls(max_attempts=data.get("max_attempts", 2))
        state.tasks_completed = data.get("tasks_completed", [])
        state.tasks_failed = data.get("tasks_failed", {})
        state.tasks_skipped = data.get("tasks_skipped", [])
        state.total_lines_written = data.get("total_lines_written", 0)
        state.total_cycles = data.get("total_cycles", 0)
        state.last_run = data.get("last_run", "")
        return state
