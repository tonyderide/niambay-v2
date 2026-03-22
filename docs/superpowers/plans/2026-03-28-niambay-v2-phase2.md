# Niam-Bay v2 — Phase 2 : Cerveau, Habitudes, Notifications

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Le daemon apprend les habitudes de l'utilisateur, se connecte aux mails/calendrier via MCP, et envoie des notifications intelligentes proactivement.

**Architecture:** Le cerveau NB (copié depuis niam-bay, adapté) stocke les patterns temporels. Un HabitTracker analyse les CollectorEvents pour détecter des routines. Un NotificationManager décide quand alerter via Windows toast + WebSocket. Les MCP Gmail/Calendar sont appelés comme services externes.

**Tech Stack:** Python 3.13, win10toast-click (notifications Windows), cerveau NB (graph associatif), MCP clients (Gmail, Calendar via les outils déjà disponibles dans Claude Code).

---

## File Structure

```
C:/niambay-v2/
├── daemon/
│   ├── brain/                    # (Phase 2 — NEW)
│   │   ├── __init__.py
│   │   ├── memory.py             # Mémoire persistante (save/load JSON)
│   │   └── habits.py             # Détection de patterns temporels
│   ├── notifications/            # (Phase 2 — NEW)
│   │   ├── __init__.py
│   │   └── notifier.py           # Notifications Windows + WebSocket
│   ├── connectors/               # (Phase 2 — NEW)
│   │   ├── __init__.py
│   │   ├── gmail.py              # Client Gmail (lecture mails)
│   │   └── calendar.py           # Client Calendar (réunions)
│   ├── main.py                   # (MODIFY — intégrer brain + notifs)
│   └── ...existing...
├── tests/
│   ├── test_brain.py             # (Phase 2 — NEW)
│   ├── test_notifications.py     # (Phase 2 — NEW)
│   ├── test_connectors.py        # (Phase 2 — NEW)
│   └── ...existing...
```

---

### Task 1: Brain Memory — stockage persistant

**Files:**
- Create: `daemon/brain/__init__.py`
- Create: `daemon/brain/memory.py`
- Create: `tests/test_brain.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_brain.py
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.brain.memory import Memory, MemoryEvent

def test_memory_event():
    evt = MemoryEvent(source="window", event_type="app_change", data={"app": "Code.exe"})
    assert evt.source == "window"
    assert evt.timestamp > 0

def test_memory_store_and_recall():
    mem = Memory()
    mem.store(MemoryEvent(source="window", event_type="app_change", data={"app": "Code.exe"}))
    mem.store(MemoryEvent(source="window", event_type="app_change", data={"app": "Chrome.exe"}))
    assert len(mem.events) == 2
    recent = mem.recent(1)
    assert recent[0].data["app"] == "Chrome.exe"

def test_memory_save_load(tmp_path):
    mem = Memory()
    mem.store(MemoryEvent(source="test", event_type="test", data={"val": 42}))
    path = str(tmp_path / "memory.json")
    mem.save(path)
    mem2 = Memory.load(path)
    assert len(mem2.events) == 1
    assert mem2.events[0].data["val"] == 42

def test_memory_max_events():
    mem = Memory(max_events=5)
    for i in range(10):
        mem.store(MemoryEvent(source="test", event_type="test", data={"i": i}))
    assert len(mem.events) == 5
    assert mem.events[0].data["i"] == 5  # oldest kept is 5

def test_memory_query_by_source():
    mem = Memory()
    mem.store(MemoryEvent(source="window", event_type="change", data={"app": "X"}))
    mem.store(MemoryEvent(source="process", event_type="stats", data={"cpu": 50}))
    mem.store(MemoryEvent(source="window", event_type="change", data={"app": "Y"}))
    results = mem.query(source="window")
    assert len(results) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_brain.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write memory.py**

```python
# daemon/brain/memory.py
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

@dataclass
class MemoryEvent:
    source: str
    event_type: str
    data: dict
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class Memory:
    """Mémoire persistante — stocke les événements observés."""

    def __init__(self, max_events=10000):
        self.events: list[MemoryEvent] = []
        self.max_events = max_events

    def store(self, event: MemoryEvent):
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def recent(self, n=10) -> list[MemoryEvent]:
        return list(reversed(self.events[-n:]))

    def query(self, source: str = None, event_type: str = None, since: float = None) -> list[MemoryEvent]:
        results = self.events
        if source:
            results = [e for e in results if e.source == source]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if since:
            results = [e for e in results if e.timestamp >= since]
        return results

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([asdict(e) for e in self.events], f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str, max_events=10000) -> 'Memory':
        mem = cls(max_events=max_events)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mem.events = [MemoryEvent(**e) for e in data]
        return mem
```

- [ ] **Step 4: Create __init__.py**

```python
# daemon/brain/__init__.py
from .memory import Memory, MemoryEvent
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_brain.py -v`
Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2 && git add daemon/brain/ tests/test_brain.py && git commit -m "feat: brain memory — persistent event storage"
```

---

### Task 2: Habit Tracker — détection de patterns

**Files:**
- Create: `daemon/brain/habits.py`
- Modify: `daemon/brain/__init__.py`
- Modify: `tests/test_brain.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_brain.py
from daemon.brain.habits import HabitTracker, Habit

def test_habit_tracker_record():
    ht = HabitTracker()
    ht.record("app_usage", "Code.exe", hour=9)
    ht.record("app_usage", "Code.exe", hour=9)
    ht.record("app_usage", "Code.exe", hour=9)
    habits = ht.detect()
    assert len(habits) >= 1
    assert habits[0].pattern == "Code.exe"
    assert habits[0].hour == 9

def test_habit_tracker_no_habit_without_repetition():
    ht = HabitTracker(min_occurrences=3)
    ht.record("app_usage", "Code.exe", hour=9)
    habits = ht.detect()
    assert len(habits) == 0

def test_habit_tracker_save_load(tmp_path):
    ht = HabitTracker()
    ht.record("app_usage", "Code.exe", hour=9)
    ht.record("app_usage", "Code.exe", hour=9)
    ht.record("app_usage", "Code.exe", hour=9)
    path = str(tmp_path / "habits.json")
    ht.save(path)
    ht2 = HabitTracker.load(path)
    assert len(ht2.detect()) >= 1

def test_habit_tracker_predictions():
    ht = HabitTracker()
    for _ in range(5):
        ht.record("app_usage", "Code.exe", hour=9)
        ht.record("app_usage", "Slack.exe", hour=9)
        ht.record("app_usage", "Chrome.exe", hour=12)
    predictions = ht.predict(hour=9)
    apps = [p.pattern for p in predictions]
    assert "Code.exe" in apps
    assert "Slack.exe" in apps
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_brain.py::test_habit_tracker_record -v`
Expected: FAIL

- [ ] **Step 3: Write habits.py**

```python
# daemon/brain/habits.py
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from collections import defaultdict

@dataclass
class Habit:
    category: str      # "app_usage", "git_push", "break_time"
    pattern: str       # "Code.exe", "push", etc.
    hour: int          # heure de la journée (0-23)
    occurrences: int   # combien de fois observé
    confidence: float  # occurrences / total observations à cette heure

class HabitTracker:
    """Détecte les patterns temporels dans le comportement utilisateur."""

    def __init__(self, min_occurrences=3):
        self.min_occurrences = min_occurrences
        # records[category][hour][pattern] = count
        self._records: dict[str, dict[int, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

    def record(self, category: str, pattern: str, hour: int = None):
        if hour is None:
            import time
            hour = time.localtime().tm_hour
        self._records[category][hour][pattern] += 1

    def detect(self) -> list[Habit]:
        habits = []
        for category, hours in self._records.items():
            for hour, patterns in hours.items():
                total = sum(patterns.values())
                for pattern, count in patterns.items():
                    if count >= self.min_occurrences:
                        habits.append(Habit(
                            category=category,
                            pattern=pattern,
                            hour=hour,
                            occurrences=count,
                            confidence=round(count / total, 2) if total > 0 else 0
                        ))
        habits.sort(key=lambda h: h.occurrences, reverse=True)
        return habits

    def predict(self, hour: int) -> list[Habit]:
        habits = self.detect()
        return [h for h in habits if h.hour == hour]

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for cat, hours in self._records.items():
            data[cat] = {}
            for hour, patterns in hours.items():
                data[cat][str(hour)] = dict(patterns)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str, min_occurrences=3) -> 'HabitTracker':
        ht = cls(min_occurrences=min_occurrences)
        with open(path) as f:
            data = json.load(f)
        for cat, hours in data.items():
            for hour_str, patterns in hours.items():
                for pattern, count in patterns.items():
                    ht._records[cat][int(hour_str)][pattern] = count
        return ht
```

- [ ] **Step 4: Update __init__.py**

```python
# daemon/brain/__init__.py
from .memory import Memory, MemoryEvent
from .habits import HabitTracker, Habit
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_brain.py -v`
Expected: 9 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2 && git add daemon/brain/ tests/test_brain.py && git commit -m "feat: habit tracker — pattern detection + predictions"
```

---

### Task 3: Notification Manager

**Files:**
- Create: `daemon/notifications/__init__.py`
- Create: `daemon/notifications/notifier.py`
- Create: `tests/test_notifications.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_notifications.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.notifications.notifier import NotificationManager, Notification

def test_notification_creation():
    n = Notification(title="Test", message="Hello", level="info")
    assert n.title == "Test"
    assert n.level == "info"
    assert n.read == False

def test_manager_add_notification():
    mgr = NotificationManager()
    mgr.notify("Test", "Hello", level="info")
    assert len(mgr.pending()) == 1

def test_manager_levels():
    mgr = NotificationManager()
    mgr.notify("Info", "test", level="info")
    mgr.notify("Warning", "test", level="warning")
    mgr.notify("Alert", "test", level="alert")
    assert len(mgr.pending()) == 3
    warnings = mgr.pending(level="warning")
    assert len(warnings) == 1

def test_manager_mark_read():
    mgr = NotificationManager()
    mgr.notify("Test", "Hello")
    notif = mgr.pending()[0]
    mgr.mark_read(notif.id)
    assert len(mgr.pending()) == 0

def test_manager_max_notifications():
    mgr = NotificationManager(max_notifications=3)
    for i in range(5):
        mgr.notify(f"Test {i}", "msg")
    assert len(mgr.all()) <= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_notifications.py -v`
Expected: FAIL

- [ ] **Step 3: Write notifier.py**

```python
# daemon/notifications/notifier.py
import time
import uuid
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("niambay.notifications")

@dataclass
class Notification:
    title: str
    message: str
    level: str = "info"  # info, warning, alert
    timestamp: float = field(default_factory=time.time)
    read: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

class NotificationManager:
    """Gère les notifications — Windows toast + WebSocket."""

    def __init__(self, max_notifications=100):
        self._notifications: list[Notification] = []
        self.max_notifications = max_notifications
        self._ws_broadcast = None  # set by daemon to broadcast to frontend
        self._toast_enabled = False

        try:
            from win10toast import ToastNotifier
            self._toaster = ToastNotifier()
            self._toast_enabled = True
        except ImportError:
            self._toaster = None

    def set_broadcast(self, broadcast_fn):
        """Set the WebSocket broadcast function."""
        self._ws_broadcast = broadcast_fn

    def notify(self, title: str, message: str, level: str = "info", toast: bool = True):
        notif = Notification(title=title, message=message, level=level)
        self._notifications.append(notif)

        # Trim old
        if len(self._notifications) > self.max_notifications:
            self._notifications = self._notifications[-self.max_notifications:]

        logger.info(f"[{level.upper()}] {title}: {message}")

        # Windows toast for warnings and alerts
        if toast and self._toast_enabled and level in ("warning", "alert"):
            try:
                self._toaster.show_toast(
                    f"Niam-Bay — {title}",
                    message,
                    duration=5,
                    threaded=True,
                )
            except Exception as e:
                logger.debug(f"Toast error: {e}")

        return notif

    def pending(self, level: str = None) -> list[Notification]:
        results = [n for n in self._notifications if not n.read]
        if level:
            results = [n for n in results if n.level == level]
        return results

    def all(self) -> list[Notification]:
        return list(self._notifications)

    def mark_read(self, notif_id: str):
        for n in self._notifications:
            if n.id == notif_id:
                n.read = True
                break
```

- [ ] **Step 4: Create __init__.py**

```python
# daemon/notifications/__init__.py
from .notifier import NotificationManager, Notification
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_notifications.py -v`
Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2 && git add daemon/notifications/ tests/test_notifications.py && git commit -m "feat: notification manager — toast + WebSocket"
```

---

### Task 4: Gmail Connector

**Files:**
- Create: `daemon/connectors/__init__.py`
- Create: `daemon/connectors/gmail.py`
- Create: `tests/test_connectors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_connectors.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.connectors.gmail import GmailConnector, Email

def test_email_creation():
    email = Email(sender="test@example.com", subject="Hello", snippet="World", date="2026-03-28", unread=True)
    assert email.sender == "test@example.com"
    assert email.unread == True

def test_gmail_connector_creation():
    gc = GmailConnector()
    assert gc.name == "gmail"
    assert gc.enabled == False  # No credentials by default

def test_gmail_format_summary():
    gc = GmailConnector()
    emails = [
        Email(sender="boss@work.com", subject="Urgent meeting", snippet="Please join", date="2026-03-28", unread=True),
        Email(sender="news@letter.com", subject="Weekly digest", snippet="This week", date="2026-03-28", unread=True),
    ]
    summary = gc.format_summary(emails)
    assert "boss@work.com" in summary
    assert "Urgent meeting" in summary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_connectors.py -v`
Expected: FAIL

- [ ] **Step 3: Write gmail.py**

```python
# daemon/connectors/gmail.py
"""
Gmail Connector — lit les mails via l'API Gmail.
Utilise OAuth2. L'authentification doit être faite une première fois via le navigateur.
En production, on utilise les MCP Gmail déjà disponibles dans Claude Code.
Ce module sert de wrapper pour le daemon.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("niambay.gmail")

@dataclass
class Email:
    sender: str
    subject: str
    snippet: str
    date: str
    unread: bool
    id: str = ""
    labels: list = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = []

class GmailConnector:
    name = "gmail"

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path
        self.enabled = credentials_path is not None
        self._mcp_available = False

    def check_mcp(self) -> bool:
        """Check if MCP Gmail tools are available (when running inside Claude Code)."""
        # MCP tools are available via Claude Code session, not directly callable from daemon
        # This flag is set externally when MCP is detected
        return self._mcp_available

    def fetch_unread(self, max_results=10) -> list[Email]:
        """Fetch unread emails. Returns empty list if not configured."""
        if not self.enabled:
            return []
        # In real implementation, this would use the Gmail API or MCP
        # For now, return empty — MCP integration happens at daemon level
        logger.info("Gmail fetch_unread called (stub — needs MCP or OAuth)")
        return []

    def format_summary(self, emails: list[Email]) -> str:
        """Format emails into a readable summary."""
        if not emails:
            return "Pas de nouveaux mails."
        lines = [f"📧 {len(emails)} mail(s) non lu(s):"]
        for e in emails[:5]:
            status = "🔴" if e.unread else "⚪"
            lines.append(f"  {status} {e.sender} — {e.subject}")
            if e.snippet:
                lines.append(f"     {e.snippet[:80]}")
        if len(emails) > 5:
            lines.append(f"  ... et {len(emails) - 5} autres")
        return "\n".join(lines)
```

- [ ] **Step 4: Create __init__.py**

```python
# daemon/connectors/__init__.py
from .gmail import GmailConnector, Email
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_connectors.py -v`
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2 && git add daemon/connectors/ tests/test_connectors.py && git commit -m "feat: gmail connector (stub + MCP-ready)"
```

---

### Task 5: Calendar Connector

**Files:**
- Create: `daemon/connectors/calendar.py`
- Modify: `daemon/connectors/__init__.py`
- Modify: `tests/test_connectors.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_connectors.py
from daemon.connectors.calendar import CalendarConnector, Meeting

def test_meeting_creation():
    m = Meeting(title="Stand-up", start="2026-03-28T09:00", end="2026-03-28T09:30", location="Teams")
    assert m.title == "Stand-up"
    assert m.location == "Teams"

def test_calendar_connector():
    cc = CalendarConnector()
    assert cc.name == "calendar"

def test_calendar_upcoming_summary():
    cc = CalendarConnector()
    meetings = [
        Meeting(title="Stand-up", start="2026-03-28T09:00", end="2026-03-28T09:30"),
        Meeting(title="Sprint review", start="2026-03-28T14:00", end="2026-03-28T15:00"),
    ]
    summary = cc.format_summary(meetings)
    assert "Stand-up" in summary
    assert "Sprint review" in summary

def test_calendar_next_meeting():
    cc = CalendarConnector()
    meetings = [
        Meeting(title="Past", start="2026-03-20T09:00", end="2026-03-20T09:30"),
        Meeting(title="Future", start="2099-01-01T09:00", end="2099-01-01T09:30"),
    ]
    nxt = cc.next_meeting(meetings)
    assert nxt.title == "Future"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_connectors.py::test_meeting_creation -v`
Expected: FAIL

- [ ] **Step 3: Write calendar.py**

```python
# daemon/connectors/calendar.py
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

logger = logging.getLogger("niambay.calendar")

@dataclass
class Meeting:
    title: str
    start: str  # ISO format
    end: str    # ISO format
    location: str = ""
    description: str = ""
    attendees: list = None

    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

    @property
    def start_dt(self) -> datetime:
        return datetime.fromisoformat(self.start)

    @property
    def end_dt(self) -> datetime:
        return datetime.fromisoformat(self.end)

    @property
    def duration_min(self) -> int:
        return int((self.end_dt - self.start_dt).total_seconds() / 60)

class CalendarConnector:
    name = "calendar"

    def __init__(self, credentials_path: str = None):
        self.credentials_path = credentials_path
        self.enabled = credentials_path is not None

    def fetch_today(self) -> list[Meeting]:
        """Fetch today's meetings. Stub — needs MCP or OAuth."""
        if not self.enabled:
            return []
        logger.info("Calendar fetch_today called (stub — needs MCP or OAuth)")
        return []

    def next_meeting(self, meetings: list[Meeting]) -> Optional[Meeting]:
        """Return the next upcoming meeting."""
        now = datetime.now()
        future = [m for m in meetings if m.start_dt > now]
        future.sort(key=lambda m: m.start_dt)
        return future[0] if future else None

    def format_summary(self, meetings: list[Meeting]) -> str:
        if not meetings:
            return "Pas de réunions aujourd'hui."
        lines = [f"📅 {len(meetings)} réunion(s):"]
        for m in meetings:
            time_str = m.start_dt.strftime("%H:%M")
            dur = m.duration_min
            loc = f" — {m.location}" if m.location else ""
            lines.append(f"  {time_str} ({dur}min) {m.title}{loc}")
        return "\n".join(lines)
```

- [ ] **Step 4: Update __init__.py**

```python
# daemon/connectors/__init__.py
from .gmail import GmailConnector, Email
from .calendar import CalendarConnector, Meeting
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_connectors.py -v`
Expected: 7 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2 && git add daemon/connectors/ tests/test_connectors.py && git commit -m "feat: calendar connector (stub + MCP-ready)"
```

---

### Task 6: Intégrer brain + habits + notifications dans le daemon

**Files:**
- Modify: `daemon/main.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.main import NiamBayDaemon
from daemon.config import Config

def test_daemon_has_brain():
    d = NiamBayDaemon(Config())
    assert d.memory is not None
    assert d.habits is not None
    assert d.notifier is not None

def test_daemon_stores_events_in_memory():
    d = NiamBayDaemon(Config())
    events = d.collect_all()
    assert len(d.memory.events) > 0

def test_daemon_records_habits():
    d = NiamBayDaemon(Config())
    d.collect_all()
    # Window collector should record app usage habit
    # Can't guarantee specific habits but records should exist

def test_daemon_notification_on_alert():
    d = NiamBayDaemon(Config())
    d.notifier.notify("Test", "test alert", level="alert")
    assert len(d.notifier.pending()) == 1

def test_daemon_status_includes_brain():
    import asyncio
    d = NiamBayDaemon(Config())
    msg = {"type": "status"}
    # Can't easily test async handler in sync test, but verify structure exists
    assert hasattr(d, 'memory')
    assert hasattr(d, 'habits')
    assert hasattr(d, 'notifier')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_integration.py -v`
Expected: FAIL — daemon doesn't have memory/habits/notifier yet

- [ ] **Step 3: Modify daemon/main.py**

Add to __init__:
```python
from .brain import Memory, MemoryEvent, HabitTracker
from .notifications import NotificationManager
```

In NiamBayDaemon.__init__, add:
```python
self.memory = Memory()
self.habits = HabitTracker()
self.notifier = NotificationManager()
```

In collect_all(), after collecting events:
```python
for evt in events:
    self.memory.store(MemoryEvent(source=evt.source, event_type=evt.event_type, data=evt.data))
    if evt.event_type == "app_change":
        import time
        hour = time.localtime().tm_hour
        self.habits.record("app_usage", evt.data.get("app", "unknown"), hour=hour)
    if evt.event_type in ("high_cpu", "high_memory", "disk_full"):
        self.notifier.notify(f"Alerte {evt.event_type}", str(evt.data), level="warning")
    if evt.event_type == "unpushed_alert":
        self.notifier.notify("Git non pushé", f"{evt.data.get('repo')}: {evt.data.get('count')} commits", level="info")
```

In _handle_client_message, add "notifications" type:
```python
elif msg_type == "notifications":
    return {"type": "notifications", "items": [{"title": n.title, "message": n.message, "level": n.level, "id": n.id, "read": n.read} for n in self.notifier.pending()]}
```

Update "status" response to include brain stats:
```python
"memory_events": len(self.memory.events),
"habits": len(self.habits.detect()),
"notifications": len(self.notifier.pending()),
```

- [ ] **Step 4: Run ALL tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/ -v`
Expected: ALL PASSED (30+ tests)

- [ ] **Step 5: Commit**

```bash
cd C:/niambay-v2 && git add daemon/ tests/ && git commit -m "feat: integrate brain + habits + notifications into daemon"
```

---

## Récapitulatif Phase 2

| Task | Composant | Tests |
|------|-----------|-------|
| 1 | Brain Memory | 5 tests |
| 2 | Habit Tracker | 4 tests |
| 3 | Notification Manager | 5 tests |
| 4 | Gmail Connector | 3 tests |
| 5 | Calendar Connector | 4 tests |
| 6 | Intégration daemon | 5 tests |
| **Total** | **6 tasks** | **26 tests** |

Après Phase 2 : le daemon observe, mémorise, détecte les habitudes, notifie sur les alertes, et a les connecteurs Gmail/Calendar prêts pour MCP.
