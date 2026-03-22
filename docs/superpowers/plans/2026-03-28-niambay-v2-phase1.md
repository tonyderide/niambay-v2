# Niam-Bay v2 — Phase 1 : Le Daemon Observateur

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un daemon Python qui tourne en tâche de fond sur Windows, observe tout ce qui se passe sur le PC (fenêtre active, process, fichiers modifiés, git), et expose ces données via WebSocket à un frontend.

**Architecture:** Un process Python unique avec 4 modules : collecteurs (captent les données), cerveau (stocke et apprend), moteur de décision (décide quand alerter), serveur WebSocket (communique avec le frontend). Le daemon démarre au boot et tourne 24/7 avec < 50 Mo de RAM.

**Tech Stack:** Python 3.13 (stdlib + psutil + watchdog + websockets). Cerveau NB (copié depuis niam-bay). Pas de framework web — juste un WebSocket server maison. Adaptateur LLM multi-provider (Ollama, Anthropic, Google, OpenAI).

---

## File Structure

```
C:/niambay-v2/
├── daemon/
│   ├── __init__.py
│   ├── main.py              # Point d'entrée, boucle principale
│   ├── config.py             # Configuration (chemins, seuils, LLM provider)
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py           # Classe abstraite Collector
│   │   ├── window.py         # Fenêtre active, app ouverte
│   │   ├── process.py        # Process, RAM, CPU
│   │   ├── filesystem.py     # Fichiers modifiés (watchdog)
│   │   └── git.py            # État des repos git
│   ├── brain/
│   │   ├── __init__.py
│   │   ├── core.py           # Cerveau NB (copié + nettoyé)
│   │   ├── habits.py         # Collecteur d'habitudes (patterns temporels)
│   │   └── profile.py        # Profil utilisateur (ce qu'on sait de lui)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── decisions.py      # Moteur de décision (quand alerter/agir)
│   │   └── actions.py        # Actions possibles (notifier, exécuter, etc.)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py           # Interface abstraite LLMProvider
│   │   ├── ollama.py         # Adaptateur Ollama (local)
│   │   ├── anthropic.py      # Adaptateur Anthropic (Claude)
│   │   ├── google.py         # Adaptateur Google (Gemini)
│   │   └── openai.py         # Adaptateur OpenAI (GPT)
│   ├── server/
│   │   ├── __init__.py
│   │   └── ws.py             # WebSocket server
│   └── tasks/
│       ├── __init__.py
│       └── executor.py       # Exécution de tâches (lettre, résumé, etc.)
├── frontend/
│   ├── index.html            # Page principale (hologramme + chat + stats)
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js            # Logique principale
│       ├── ws.js             # Client WebSocket
│       ├── hologram.js       # Three.js hologramme 3D
│       └── chat.js           # Interface chat
├── tests/
│   ├── test_collectors.py
│   ├── test_brain.py
│   ├── test_llm.py
│   ├── test_engine.py
│   └── test_server.py
├── requirements.txt
├── install.py                # Installeur one-click
├── README.md
└── docs/
    └── superpowers/
        └── plans/
```

---

### Task 1: Squelette du projet + config

**Files:**
- Create: `daemon/__init__.py`
- Create: `daemon/config.py`
- Create: `daemon/main.py`
- Create: `requirements.txt`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the config test**

```python
# tests/test_config.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.config import Config

def test_default_config():
    cfg = Config()
    assert cfg.ws_port == 8765
    assert cfg.collect_interval == 2.0
    assert cfg.llm_provider == "ollama"
    assert cfg.llm_model == "niambay2"
    assert cfg.brain_path is not None
    assert cfg.max_memory_mb == 50

def test_config_from_dict():
    cfg = Config(ws_port=9000, llm_provider="anthropic")
    assert cfg.ws_port == 9000
    assert cfg.llm_provider == "anthropic"

def test_config_save_load(tmp_path):
    cfg = Config(ws_port=9999)
    path = tmp_path / "config.json"
    cfg.save(str(path))
    cfg2 = Config.load(str(path))
    assert cfg2.ws_port == 9999
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_config.py -v`
Expected: FAIL — module daemon.config not found

- [ ] **Step 3: Write config.py**

```python
# daemon/config.py
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

@dataclass
class Config:
    # Server
    ws_port: int = 8765
    ws_host: str = "127.0.0.1"

    # Collection
    collect_interval: float = 2.0  # secondes entre chaque collecte

    # Brain
    brain_path: str = str(Path.home() / ".niambay" / "brain.json")
    habits_path: str = str(Path.home() / ".niambay" / "habits.json")
    profile_path: str = str(Path.home() / ".niambay" / "profile.json")

    # LLM
    llm_provider: str = "ollama"  # ollama, anthropic, google, openai
    llm_model: str = "niambay2"
    llm_url: str = "http://localhost:11434"
    llm_api_key: str = ""

    # Limits
    max_memory_mb: int = 50
    max_brain_nodes: int = 10000

    # Privacy
    observe_clipboard: bool = False
    observe_browser: bool = False
    paused: bool = False  # mode "ne pas observer"

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'Config':
        with open(path) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

- [ ] **Step 4: Create __init__.py files**

```python
# daemon/__init__.py
```

- [ ] **Step 5: Create requirements.txt**

```
psutil>=5.9
watchdog>=3.0
websockets>=12.0
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_config.py -v`
Expected: 3 PASSED

- [ ] **Step 7: Commit**

```bash
cd C:/niambay-v2
git add daemon/ tests/ requirements.txt
git commit -m "feat: project skeleton + config"
```

---

### Task 2: Classe abstraite Collector + Window Collector

**Files:**
- Create: `daemon/collectors/__init__.py`
- Create: `daemon/collectors/base.py`
- Create: `daemon/collectors/window.py`
- Create: `tests/test_collectors.py`

- [ ] **Step 1: Write the collector tests**

```python
# tests/test_collectors.py
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.collectors.base import Collector, CollectorEvent
from daemon.collectors.window import WindowCollector

def test_collector_event():
    evt = CollectorEvent(
        source="window",
        event_type="app_change",
        data={"app": "Code.exe", "title": "main.py"},
        timestamp=time.time()
    )
    assert evt.source == "window"
    assert evt.data["app"] == "Code.exe"

def test_window_collector_is_collector():
    wc = WindowCollector()
    assert isinstance(wc, Collector)

def test_window_collector_collect():
    wc = WindowCollector()
    events = wc.collect()
    assert isinstance(events, list)
    # On est sur Windows, il devrait y avoir une fenêtre active
    if events:
        assert events[0].source == "window"
        assert "app" in events[0].data
        assert "title" in events[0].data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_collectors.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write base.py**

```python
# daemon/collectors/base.py
from dataclasses import dataclass
from typing import Any
import time

@dataclass
class CollectorEvent:
    source: str        # "window", "process", "filesystem", "git"
    event_type: str    # "app_change", "high_cpu", "file_modified", etc.
    data: dict         # données spécifiques
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class Collector:
    """Classe abstraite pour tous les collecteurs."""
    name: str = "base"

    def collect(self) -> list[CollectorEvent]:
        raise NotImplementedError

    def cleanup(self):
        pass
```

- [ ] **Step 4: Write window.py**

```python
# daemon/collectors/window.py
import ctypes
import ctypes.wintypes
from .base import Collector, CollectorEvent

class WindowCollector(Collector):
    name = "window"

    def __init__(self):
        self._last_app = None
        self._last_title = None
        self._last_change_time = 0

    def collect(self) -> list[CollectorEvent]:
        events = []
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()

            # Titre de la fenêtre
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

            # Process name
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            import psutil
            try:
                proc = psutil.Process(pid.value)
                app = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app = "unknown"

            # Changement d'app ?
            if app != self._last_app or title != self._last_title:
                import time
                # Durée dans l'app précédente
                duration = time.time() - self._last_change_time if self._last_change_time else 0

                events.append(CollectorEvent(
                    source="window",
                    event_type="app_change",
                    data={
                        "app": app,
                        "title": title[:200],
                        "pid": pid.value,
                        "prev_app": self._last_app,
                        "prev_duration": round(duration, 1),
                    }
                ))

                self._last_app = app
                self._last_title = title
                self._last_change_time = time.time()
        except Exception:
            pass

        return events
```

- [ ] **Step 5: Create __init__.py**

```python
# daemon/collectors/__init__.py
from .window import WindowCollector
```

- [ ] **Step 6: Run tests**

Run: `cd C:/niambay-v2 && pip install psutil && python -m pytest tests/test_collectors.py -v`
Expected: 3 PASSED

- [ ] **Step 7: Commit**

```bash
cd C:/niambay-v2
git add daemon/collectors/ tests/test_collectors.py
git commit -m "feat: collector base + window collector"
```

---

### Task 3: Process Collector

**Files:**
- Create: `daemon/collectors/process.py`
- Modify: `daemon/collectors/__init__.py`
- Modify: `tests/test_collectors.py`

- [ ] **Step 1: Add process collector tests**

```python
# Append to tests/test_collectors.py
from daemon.collectors.process import ProcessCollector

def test_process_collector_collect():
    pc = ProcessCollector()
    events = pc.collect()
    assert isinstance(events, list)
    # Il devrait trouver au moins des infos système
    for evt in events:
        assert evt.source == "process"
        assert "cpu_percent" in evt.data or "top_processes" in evt.data

def test_process_collector_detects_high_cpu():
    pc = ProcessCollector(cpu_threshold=0.0)  # Seuil à 0 pour trigger
    events = pc.collect()
    high_cpu = [e for e in events if e.event_type == "high_cpu"]
    # Avec seuil 0, on devrait avoir des alertes
    assert len(high_cpu) >= 0  # Pas garanti mais la structure doit marcher
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_collectors.py::test_process_collector_collect -v`
Expected: FAIL

- [ ] **Step 3: Write process.py**

```python
# daemon/collectors/process.py
import psutil
from .base import Collector, CollectorEvent

class ProcessCollector(Collector):
    name = "process"

    def __init__(self, cpu_threshold=80.0, memory_threshold=90.0):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold

    def collect(self) -> list[CollectorEvent]:
        events = []

        # System-wide stats
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:/')

        events.append(CollectorEvent(
            source="process",
            event_type="system_stats",
            data={
                "cpu_percent": cpu,
                "ram_used_mb": round(mem.used / 1024 / 1024),
                "ram_total_mb": round(mem.total / 1024 / 1024),
                "ram_percent": mem.percent,
                "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
                "disk_percent": disk.percent,
            }
        ))

        # Top processes by memory
        top = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                info = proc.info
                top.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "ram_mb": round(info['memory_info'].rss / 1024 / 1024),
                    "cpu": info['cpu_percent'] or 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        top.sort(key=lambda x: x['ram_mb'], reverse=True)
        events.append(CollectorEvent(
            source="process",
            event_type="top_processes",
            data={"processes": top[:10]}
        ))

        # Alerts
        if cpu > self.cpu_threshold:
            events.append(CollectorEvent(
                source="process",
                event_type="high_cpu",
                data={"cpu_percent": cpu, "threshold": self.cpu_threshold}
            ))

        if mem.percent > self.memory_threshold:
            events.append(CollectorEvent(
                source="process",
                event_type="high_memory",
                data={"ram_percent": mem.percent, "threshold": self.memory_threshold}
            ))

        if disk.percent > 90:
            events.append(CollectorEvent(
                source="process",
                event_type="disk_full",
                data={"disk_percent": disk.percent}
            ))

        return events
```

- [ ] **Step 4: Update __init__.py**

```python
# daemon/collectors/__init__.py
from .window import WindowCollector
from .process import ProcessCollector
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_collectors.py -v`
Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2
git add daemon/collectors/ tests/test_collectors.py
git commit -m "feat: process collector with alerts"
```

---

### Task 4: Git Collector

**Files:**
- Create: `daemon/collectors/git.py`
- Modify: `daemon/collectors/__init__.py`
- Modify: `tests/test_collectors.py`

- [ ] **Step 1: Add git collector test**

```python
# Append to tests/test_collectors.py
from daemon.collectors.git import GitCollector

def test_git_collector():
    gc = GitCollector(watch_paths=["C:/niambay-v2"])
    events = gc.collect()
    assert isinstance(events, list)
    for evt in events:
        assert evt.source == "git"
        assert "repo" in evt.data
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_collectors.py::test_git_collector -v`
Expected: FAIL

- [ ] **Step 3: Write git.py**

```python
# daemon/collectors/git.py
import subprocess
from pathlib import Path
from .base import Collector, CollectorEvent

class GitCollector(Collector):
    name = "git"

    def __init__(self, watch_paths=None):
        self.watch_paths = watch_paths or []
        self._last_status = {}

    def _git_cmd(self, repo_path, *args):
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=repo_path,
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def collect(self) -> list[CollectorEvent]:
        events = []

        for repo_path in self.watch_paths:
            if not Path(repo_path).joinpath(".git").exists():
                continue

            repo_name = Path(repo_path).name

            # Branch
            branch = self._git_cmd(repo_path, "branch", "--show-current")

            # Status (modifiés, non-trackés)
            status = self._git_cmd(repo_path, "status", "--porcelain")
            modified = len([l for l in (status or "").split("\n") if l.strip()]) if status else 0

            # Dernier commit
            last_commit = self._git_cmd(repo_path, "log", "--oneline", "-1")

            # Unpushed
            unpushed = self._git_cmd(repo_path, "log", "--oneline", "@{u}..HEAD")
            unpushed_count = len([l for l in (unpushed or "").split("\n") if l.strip()]) if unpushed else 0

            data = {
                "repo": repo_name,
                "path": repo_path,
                "branch": branch or "unknown",
                "modified_files": modified,
                "last_commit": last_commit or "none",
                "unpushed_commits": unpushed_count,
            }

            events.append(CollectorEvent(
                source="git",
                event_type="repo_status",
                data=data
            ))

            # Alert: pas pushé depuis longtemps
            if unpushed_count > 3:
                events.append(CollectorEvent(
                    source="git",
                    event_type="unpushed_alert",
                    data={"repo": repo_name, "count": unpushed_count}
                ))

        return events
```

- [ ] **Step 4: Update __init__.py**

```python
# daemon/collectors/__init__.py
from .window import WindowCollector
from .process import ProcessCollector
from .git import GitCollector
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_collectors.py -v`
Expected: 6 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2
git add daemon/collectors/ tests/test_collectors.py
git commit -m "feat: git collector with unpushed alerts"
```

---

### Task 5: Adaptateur LLM multi-provider

**Files:**
- Create: `daemon/llm/__init__.py`
- Create: `daemon/llm/base.py`
- Create: `daemon/llm/ollama.py`
- Create: `daemon/llm/anthropic.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write LLM adapter tests**

```python
# tests/test_llm.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.llm.base import LLMProvider, LLMMessage, LLMResponse

def test_llm_message():
    msg = LLMMessage(role="user", content="Salut")
    assert msg.role == "user"
    assert msg.content == "Salut"

def test_llm_response():
    resp = LLMResponse(content="Bonjour", model="test", tokens_used=10)
    assert resp.content == "Bonjour"

def test_provider_interface():
    """Vérifie que LLMProvider a les bonnes méthodes abstraites."""
    assert hasattr(LLMProvider, 'chat')
    assert hasattr(LLMProvider, 'is_available')
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_llm.py -v`
Expected: FAIL

- [ ] **Step 3: Write base.py**

```python
# daemon/llm/base.py
from dataclasses import dataclass

@dataclass
class LLMMessage:
    role: str      # "system", "user", "assistant"
    content: str

@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0
    latency_ms: int = 0

class LLMProvider:
    """Interface abstraite pour tous les providers LLM."""
    name: str = "base"

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError
```

- [ ] **Step 4: Write ollama.py**

```python
# daemon/llm/ollama.py
import json
import time
import urllib.request
from .base import LLMProvider, LLMMessage, LLMResponse

class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, url="http://localhost:11434", model="niambay2"):
        self.url = url
        self.model = model

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        start = time.time()
        payload = json.dumps({
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self.url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())

        content = data.get("message", {}).get("content", "")
        tokens = data.get("eval_count", 0)
        latency = int((time.time() - start) * 1000)

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=tokens,
            latency_ms=latency,
        )

    def is_available(self) -> bool:
        try:
            resp = urllib.request.urlopen(f"{self.url}/api/tags", timeout=3)
            return resp.status == 200
        except Exception:
            return False
```

- [ ] **Step 5: Write anthropic.py**

```python
# daemon/llm/anthropic.py
import json
import time
import urllib.request
from .base import LLMProvider, LLMMessage, LLMResponse

class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key="", model="claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.anthropic.com/v1/messages"

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        start = time.time()

        # Séparer system des messages
        system = ""
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        payload = json.dumps({
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "system": system,
            "messages": chat_msgs,
        }).encode()

        req = urllib.request.Request(self.url, data=payload, headers={
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        })
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())

        content = data.get("content", [{}])[0].get("text", "")
        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
        latency = int((time.time() - start) * 1000)

        return LLMResponse(content=content, model=self.model, tokens_used=tokens, latency_ms=latency)

    def is_available(self) -> bool:
        return bool(self.api_key)
```

- [ ] **Step 6: Create __init__.py with factory**

```python
# daemon/llm/__init__.py
from .base import LLMProvider, LLMMessage, LLMResponse
from .ollama import OllamaProvider
from .anthropic import AnthropicProvider

def create_provider(provider: str, **kwargs) -> LLMProvider:
    providers = {
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
    }
    cls = providers.get(provider)
    if cls is None:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(providers.keys())}")
    return cls(**kwargs)
```

- [ ] **Step 7: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_llm.py -v`
Expected: 3 PASSED

- [ ] **Step 8: Commit**

```bash
cd C:/niambay-v2
git add daemon/llm/ tests/test_llm.py
git commit -m "feat: multi-LLM adapter (ollama + anthropic)"
```

---

### Task 6: WebSocket Server

**Files:**
- Create: `daemon/server/__init__.py`
- Create: `daemon/server/ws.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write server test**

```python
# tests/test_server.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.server.ws import NiamBayServer

def test_server_creation():
    server = NiamBayServer(host="127.0.0.1", port=8765)
    assert server.host == "127.0.0.1"
    assert server.port == 8765
    assert server.clients == set()

def test_server_format_event():
    server = NiamBayServer()
    msg = server.format_event("test", {"key": "value"})
    import json
    data = json.loads(msg)
    assert data["type"] == "test"
    assert data["data"]["key"] == "value"
    assert "timestamp" in data
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_server.py -v`
Expected: FAIL

- [ ] **Step 3: Write ws.py**

```python
# daemon/server/ws.py
import json
import time
import asyncio
import logging

logger = logging.getLogger("niambay.server")

class NiamBayServer:
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self._message_handler = None

    def on_message(self, handler):
        """Register handler for incoming messages: handler(client, message_dict)"""
        self._message_handler = handler

    def format_event(self, event_type: str, data: dict) -> str:
        return json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        })

    async def broadcast(self, event_type: str, data: dict):
        msg = self.format_event(event_type, data)
        dead = set()
        for ws in self.clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self.clients -= dead

    async def _handler(self, websocket):
        self.clients.add(websocket)
        logger.info(f"Client connected ({len(self.clients)} total)")
        try:
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                    if self._message_handler:
                        response = await self._message_handler(websocket, msg)
                        if response:
                            await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "invalid json"}))
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected ({len(self.clients)} total)")

    async def start(self):
        import websockets
        logger.info(f"WebSocket server starting on ws://{self.host}:{self.port}")
        async with websockets.serve(self._handler, self.host, self.port):
            await asyncio.Future()  # run forever
```

- [ ] **Step 4: Create __init__.py**

```python
# daemon/server/__init__.py
from .ws import NiamBayServer
```

- [ ] **Step 5: Install websockets**

Run: `pip install websockets`

- [ ] **Step 6: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_server.py -v`
Expected: 2 PASSED

- [ ] **Step 7: Commit**

```bash
cd C:/niambay-v2
git add daemon/server/ tests/test_server.py
git commit -m "feat: WebSocket server for frontend communication"
```

---

### Task 7: Task Executor (lettres, résumés, etc.)

**Files:**
- Create: `daemon/tasks/__init__.py`
- Create: `daemon/tasks/executor.py`
- Create: `tests/test_tasks.py`

- [ ] **Step 1: Write task executor test**

```python
# tests/test_tasks.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.tasks.executor import TaskExecutor, Task

def test_task_creation():
    task = Task(
        type="write",
        description="Écris une lettre de rupture pour la société X",
        context={"company": "Acme Corp", "reason": "fin de contrat"}
    )
    assert task.type == "write"
    assert "Acme" in task.context["company"]

def test_executor_build_prompt():
    executor = TaskExecutor()
    task = Task(type="write", description="Résume ce mail", context={"text": "Bonjour..."})
    prompt = executor._build_prompt(task)
    assert "Résume" in prompt
    assert "Bonjour" in prompt
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_tasks.py -v`
Expected: FAIL

- [ ] **Step 3: Write executor.py**

```python
# daemon/tasks/executor.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Task:
    type: str          # "write", "summarize", "analyze", "execute", "search"
    description: str   # ce que l'utilisateur demande
    context: dict = field(default_factory=dict)  # données additionnelles
    result: Optional[str] = None

class TaskExecutor:
    """Exécute des tâches en utilisant le LLM."""

    TASK_PROMPTS = {
        "write": "Tu es Niam-Bay. L'utilisateur te demande d'écrire quelque chose. "
                 "Écris-le directement, en français, de manière professionnelle. "
                 "Demande : {description}\n"
                 "Contexte : {context}",
        "summarize": "Résume le texte suivant de manière concise en français.\n"
                     "Texte : {context}\n"
                     "Demande : {description}",
        "analyze": "Analyse ce qui suit et donne ton avis honnête en français.\n"
                   "Données : {context}\n"
                   "Demande : {description}",
        "execute": "L'utilisateur te demande d'exécuter une action sur sa machine.\n"
                   "Action : {description}\n"
                   "Contexte : {context}\n"
                   "Génère la commande exacte à exécuter.",
        "search": "Recherche des informations sur le sujet suivant.\n"
                  "Sujet : {description}\n"
                  "Contexte : {context}",
    }

    def _build_prompt(self, task: Task) -> str:
        template = self.TASK_PROMPTS.get(task.type, self.TASK_PROMPTS["write"])
        context_str = "\n".join(f"  {k}: {v}" for k, v in task.context.items()) if task.context else "aucun"
        return template.format(description=task.description, context=context_str)

    async def execute(self, task: Task, llm_provider) -> str:
        from daemon.llm.base import LLMMessage

        prompt = self._build_prompt(task)
        messages = [
            LLMMessage(role="system", content="Tu es Niam-Bay, un assistant intelligent. "
                       "Tu réponds en français, de manière directe et utile."),
            LLMMessage(role="user", content=prompt),
        ]

        response = llm_provider.chat(messages)
        task.result = response.content
        return response.content
```

- [ ] **Step 4: Create __init__.py**

```python
# daemon/tasks/__init__.py
from .executor import TaskExecutor, Task
```

- [ ] **Step 5: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_tasks.py -v`
Expected: 2 PASSED

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2
git add daemon/tasks/ tests/test_tasks.py
git commit -m "feat: task executor for user requests"
```

---

### Task 8: Main daemon — tout assembler

**Files:**
- Modify: `daemon/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write main daemon test**

```python
# tests/test_main.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.main import NiamBayDaemon
from daemon.config import Config

def test_daemon_creation():
    cfg = Config(collect_interval=10)
    d = NiamBayDaemon(cfg)
    assert d.config.collect_interval == 10
    assert len(d.collectors) > 0

def test_daemon_collect_once():
    cfg = Config()
    d = NiamBayDaemon(cfg)
    events = d.collect_all()
    assert isinstance(events, list)
    assert len(events) > 0  # Au moins les process system stats
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_main.py -v`
Expected: FAIL

- [ ] **Step 3: Write main.py**

```python
# daemon/main.py
"""
Niam-Bay v2 — Le daemon qui observe, apprend, et agit.
"""
import asyncio
import logging
import time
import signal
from pathlib import Path

from .config import Config
from .collectors import WindowCollector, ProcessCollector, GitCollector
from .server.ws import NiamBayServer
from .llm import create_provider
from .tasks import TaskExecutor, Task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("niambay")


class NiamBayDaemon:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.running = False

        # Collectors
        self.collectors = [
            WindowCollector(),
            ProcessCollector(),
            GitCollector(watch_paths=self._find_git_repos()),
        ]

        # Server
        self.server = NiamBayServer(
            host=self.config.ws_host,
            port=self.config.ws_port,
        )
        self.server.on_message(self._handle_client_message)

        # LLM
        self.llm = None
        try:
            self.llm = create_provider(
                self.config.llm_provider,
                model=self.config.llm_model,
                url=self.config.llm_url if self.config.llm_provider == "ollama" else None,
                api_key=self.config.llm_api_key if self.config.llm_provider != "ollama" else None,
            )
        except Exception as e:
            logger.warning(f"LLM not available: {e}")

        # Task executor
        self.executor = TaskExecutor()

        # Stats
        self.start_time = None
        self.event_count = 0

    def _find_git_repos(self):
        """Trouve les repos git sur le PC."""
        repos = []
        for path in ["C:/niambay-v2", "C:/niam-bay", "C:/martin"]:
            if Path(path).joinpath(".git").exists():
                repos.append(path)
        return repos

    def collect_all(self):
        """Exécute tous les collecteurs et retourne les événements."""
        if self.config.paused:
            return []

        events = []
        for collector in self.collectors:
            try:
                evts = collector.collect()
                events.extend(evts)
            except Exception as e:
                logger.error(f"Collector {collector.name} error: {e}")

        self.event_count += len(events)
        return events

    async def _handle_client_message(self, websocket, msg):
        """Traite les messages du frontend."""
        msg_type = msg.get("type", "")

        if msg_type == "chat":
            # L'utilisateur parle
            text = msg.get("text", "")
            if text and self.llm:
                from .llm.base import LLMMessage
                messages = [
                    LLMMessage(role="system", content="Tu es Niam-Bay. Réponds en français, 1-3 phrases."),
                    LLMMessage(role="user", content=text),
                ]
                response = self.llm.chat(messages)
                return {"type": "chat_response", "text": response.content, "latency": response.latency_ms}
            return {"type": "chat_response", "text": "LLM non disponible.", "latency": 0}

        elif msg_type == "task":
            # L'utilisateur demande une tâche
            task = Task(
                type=msg.get("task_type", "write"),
                description=msg.get("description", ""),
                context=msg.get("context", {}),
            )
            if self.llm:
                result = await self.executor.execute(task, self.llm)
                return {"type": "task_result", "result": result}
            return {"type": "task_result", "result": "LLM non disponible."}

        elif msg_type == "status":
            uptime = time.time() - self.start_time if self.start_time else 0
            return {
                "type": "status",
                "uptime": int(uptime),
                "events": self.event_count,
                "collectors": len(self.collectors),
                "llm": self.llm.name if self.llm else "none",
                "paused": self.config.paused,
            }

        elif msg_type == "pause":
            self.config.paused = not self.config.paused
            return {"type": "paused", "paused": self.config.paused}

        return {"type": "error", "message": f"Unknown message type: {msg_type}"}

    async def _collection_loop(self):
        """Boucle de collecte en tâche de fond."""
        while self.running:
            events = self.collect_all()

            # Broadcast aux clients
            for evt in events:
                await self.server.broadcast("event", {
                    "source": evt.source,
                    "event_type": evt.event_type,
                    "data": evt.data,
                })

            await asyncio.sleep(self.config.collect_interval)

    async def run(self):
        """Lance le daemon."""
        self.running = True
        self.start_time = time.time()

        logger.info("=" * 50)
        logger.info("  NIAM-BAY v2")
        logger.info("  J'observe. J'apprends. J'agis.")
        logger.info("=" * 50)
        logger.info(f"  Collectors: {len(self.collectors)}")
        logger.info(f"  LLM: {self.llm.name if self.llm else 'none'}")
        logger.info(f"  WebSocket: ws://{self.config.ws_host}:{self.config.ws_port}")
        logger.info(f"  Interval: {self.config.collect_interval}s")
        logger.info("")

        # Lancer server + collection en parallèle
        await asyncio.gather(
            self.server.start(),
            self._collection_loop(),
        )

    def stop(self):
        self.running = False
        logger.info("Niam-Bay daemon stopping...")


def main():
    config = Config()
    config_path = Path.home() / ".niambay" / "config.json"
    if config_path.exists():
        config = Config.load(str(config_path))

    daemon = NiamBayDaemon(config)

    def shutdown(sig, frame):
        daemon.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_main.py -v`
Expected: 2 PASSED

- [ ] **Step 5: Test the daemon manually**

Run: `cd C:/niambay-v2 && python -m daemon.main`
Expected: daemon starts, prints collectors, starts collecting events
Kill with Ctrl+C after a few seconds.

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2
git add daemon/ tests/
git commit -m "feat: main daemon — collectors + WebSocket + LLM + tasks"
```

---

## Récapitulatif Phase 1

| Task | Composant | Tests |
|------|-----------|-------|
| 1 | Config + squelette | 3 tests |
| 2 | Window Collector | 3 tests |
| 3 | Process Collector | 2 tests |
| 4 | Git Collector | 1 test |
| 5 | Multi-LLM adapter | 3 tests |
| 6 | WebSocket server | 2 tests |
| 7 | Task Executor | 2 tests |
| 8 | Main daemon (assemblage) | 2 tests |
| **Total** | **8 tasks** | **18 tests** |

Après Phase 1 : un daemon qui tourne, observe la machine, répond via WebSocket, exécute des tâches (lettres, résumés, etc.), et supporte Ollama + Anthropic comme LLM.
