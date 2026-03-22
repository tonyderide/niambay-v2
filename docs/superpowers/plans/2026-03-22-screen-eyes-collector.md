# Screen Eyes Collector — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un collecteur "eyes" qui prend des screenshots périodiques, les envoie au LLM (Gemini vision), et stocke ce que l'utilisateur fait à l'écran — remplaçant le besoin d'APIs spécifiques.

**Architecture:** Un ScreenCollector prend un screenshot via mss (rapide, cross-platform), le redimensionne pour économiser les tokens, l'encode en base64, et l'envoie au LLM vision (Gemini) pour analyse. Le résultat est un CollectorEvent avec les infos extraites (app, contenu, contexte).

**Tech Stack:** Python mss (screenshots rapides), Pillow (resize), Gemini Vision API (analyse d'image), base64.

---

## File Structure

```
C:/niambay-v2/
├── daemon/
│   ├── collectors/
│   │   ├── screen.py          # (NEW) Screenshot + LLM vision analysis
│   │   └── __init__.py        # (MODIFY) Add ScreenCollector
│   ├── llm/
│   │   └── google.py          # (MODIFY) Add vision support
│   └── main.py                # (MODIFY) Add ScreenCollector + config
├── tests/
│   └── test_screen.py         # (NEW)
```

---

### Task 1: Screenshot capture module

**Files:**
- Create: `daemon/collectors/screen.py`
- Create: `tests/test_screen.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_screen.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.collectors.screen import ScreenCollector

def test_screen_collector_creation():
    sc = ScreenCollector(interval=30, resize_width=800)
    assert sc.name == "screen"
    assert sc.interval == 30
    assert sc.resize_width == 800

def test_screen_capture_returns_bytes():
    sc = ScreenCollector()
    img_bytes, width, height = sc.capture()
    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 0
    assert width > 0
    assert height > 0

def test_screen_capture_resize():
    sc = ScreenCollector(resize_width=400)
    img_bytes, width, height = sc.capture()
    assert width == 400

def test_screen_to_base64():
    sc = ScreenCollector(resize_width=400)
    b64 = sc.capture_base64()
    assert isinstance(b64, str)
    assert len(b64) > 100
    import base64
    decoded = base64.b64decode(b64)
    assert len(decoded) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_screen.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Install deps + write screen.py**

```bash
pip install mss Pillow
```

```python
# daemon/collectors/screen.py
import io
import time
import base64
import logging
from .base import Collector, CollectorEvent

logger = logging.getLogger("niambay.screen")

class ScreenCollector(Collector):
    """Capture l'écran et analyse via LLM vision."""
    name = "screen"

    def __init__(self, interval=30, resize_width=800, vision_provider=None):
        self.interval = interval  # seconds between captures
        self.resize_width = resize_width
        self.vision_provider = vision_provider  # LLM with vision support
        self._last_capture_time = 0
        self._last_analysis = ""

    def capture(self) -> tuple[bytes, int, int]:
        """Capture primary screen, resize, return (jpeg_bytes, width, height)."""
        import mss
        from PIL import Image

        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        # Resize to save tokens
        if self.resize_width and img.width > self.resize_width:
            ratio = self.resize_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((self.resize_width, new_height), Image.LANCZOS)

        # Encode as JPEG (smaller than PNG)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        jpeg_bytes = buf.getvalue()

        return jpeg_bytes, img.width, img.height

    def capture_base64(self) -> str:
        """Capture and return as base64 string."""
        jpeg_bytes, _, _ = self.capture()
        return base64.b64encode(jpeg_bytes).decode()

    def analyze(self, image_b64: str) -> str:
        """Send screenshot to LLM vision for analysis."""
        if not self.vision_provider:
            return ""

        try:
            result = self.vision_provider.analyze_image(
                image_b64,
                prompt=(
                    "Décris en 2-3 phrases ce que tu vois à l'écran. "
                    "Mentionne: l'application active, ce que l'utilisateur fait, "
                    "et tout élément important visible (notifications, erreurs, données). "
                    "Réponds en français."
                )
            )
            return result
        except Exception as e:
            logger.warning(f"Vision analysis failed: {e}")
            return ""

    def collect(self) -> list[CollectorEvent]:
        """Capture + analyze if interval elapsed."""
        now = time.time()
        if now - self._last_capture_time < self.interval:
            return []

        self._last_capture_time = now
        events = []

        try:
            image_b64 = self.capture_base64()
            analysis = self.analyze(image_b64)

            if analysis:
                self._last_analysis = analysis
                events.append(CollectorEvent(
                    source="screen",
                    event_type="screen_analysis",
                    data={
                        "analysis": analysis,
                        "image_size_kb": len(image_b64) * 3 // 4 // 1024,
                    }
                ))

        except Exception as e:
            logger.error(f"Screen capture failed: {e}")

        return events
```

- [ ] **Step 4: Run tests**

Run: `cd C:/niambay-v2 && pip install mss Pillow && python -m pytest tests/test_screen.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
cd C:/niambay-v2
git add daemon/collectors/screen.py tests/test_screen.py
git commit -m "feat: screen capture collector with resize"
```

---

### Task 2: Gemini Vision support

**Files:**
- Modify: `daemon/llm/google.py` — add analyze_image method

- [ ] **Step 1: Write test**

```python
# Append to tests/test_screen.py
from daemon.llm.google import GoogleProvider

def test_google_has_vision():
    gp = GoogleProvider(api_key="test")
    assert hasattr(gp, 'analyze_image')
```

- [ ] **Step 2: Add analyze_image to GoogleProvider**

```python
# Add to daemon/llm/google.py GoogleProvider class:

def analyze_image(self, image_base64: str, prompt: str = "Describe what you see.") -> str:
    """Send an image to Gemini Vision for analysis."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    body = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": image_base64
                    }
                }
            ]
        }]
    }

    payload = json.dumps(body).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())

    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        if parts:
            return parts[0].get("text", "")
    return ""
```

- [ ] **Step 3: Run tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_screen.py -v`
Expected: 5 PASSED

- [ ] **Step 4: Commit**

```bash
cd C:/niambay-v2
git add daemon/llm/google.py tests/test_screen.py
git commit -m "feat: Gemini Vision — analyze_image support"
```

---

### Task 3: Integrate screen collector into daemon

**Files:**
- Modify: `daemon/collectors/__init__.py`
- Modify: `daemon/config.py`
- Modify: `daemon/main.py`

- [ ] **Step 1: Update collectors __init__.py**

```python
# Add to daemon/collectors/__init__.py
from .screen import ScreenCollector
```

- [ ] **Step 2: Add config fields**

Add to daemon/config.py Config:
```python
observe_screen: bool = True
screen_interval: int = 30  # seconds between screenshots
screen_resize_width: int = 800
```

- [ ] **Step 3: Update daemon/main.py**

In NiamBayDaemon.__init__, add ScreenCollector to collectors list:
```python
from .collectors import ScreenCollector

# In __init__, after other collectors:
if self.config.observe_screen:
    vision = None
    # Use Gemini for vision if available
    if getattr(self.config, 'gemini_api_key', ''):
        from .llm.google import GoogleProvider
        vision = GoogleProvider(api_key=self.config.gemini_api_key)
    self.collectors.append(ScreenCollector(
        interval=self.config.screen_interval,
        resize_width=self.config.screen_resize_width,
        vision_provider=vision,
    ))
```

Add "screenshot" message type handler:
```python
elif msg_type == "screenshot":
    # Take screenshot on demand and analyze
    sc = next((c for c in self.collectors if c.name == "screen"), None)
    if sc:
        b64 = sc.capture_base64()
        analysis = sc.analyze(b64)
        return {"type": "screenshot_result", "analysis": analysis, "image": b64}
    return {"type": "screenshot_result", "analysis": "Screen collector not available", "image": ""}
```

- [ ] **Step 4: Update settings.js**

Add in Observation section:
- Screen capture toggle
- Interval slider (10-120 seconds)
- "Take screenshot now" button

- [ ] **Step 5: Run all tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/ -v`
Expected: ALL pass

- [ ] **Step 6: Commit**

```bash
cd C:/niambay-v2
git add daemon/ tests/ frontend/
git commit -m "feat: screen eyes — screenshot + Gemini vision integrated"
```

---

## Récapitulatif

| Task | Composant | Tests |
|------|-----------|-------|
| 1 | Screenshot capture + resize | 4 |
| 2 | Gemini Vision analyze_image | 1 |
| 3 | Daemon integration | existing |
| **Total** | **3 tasks** | **5 new tests** |

Après ce plan : le daemon prend des screenshots toutes les 30s, les envoie à Gemini Vision, et stocke l'analyse. Il "voit" tout ce que tu fais — Kraken, mails, code — sans API spécifique.
