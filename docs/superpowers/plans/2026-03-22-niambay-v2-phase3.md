# Niam-Bay v2 — Phase 3 : Hologramme 3D + Voix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un frontend web (Chrome) avec un hologramme 3D animé (Three.js), chat texte + voix (Whisper STT, pyttsx3 TTS), connecté au daemon via WebSocket.

**Architecture:** Le frontend est une app web statique servie par le daemon Python (HTTP simple). Three.js pour l'hologramme. Le daemon gère le STT/TTS côté Python et streame audio/texte via WebSocket. Le micro fonctionne dans Chrome (pas dans Tauri).

**Tech Stack:** HTML/CSS/JS (vanilla, pas de framework), Three.js (CDN), WebSocket client. Côté daemon: http.server pour servir le frontend, Whisper (STT), pyttsx3 (TTS).

---

## File Structure

```
C:/niambay-v2/
├── frontend/
│   ├── index.html            # Page unique — hologramme + chat + stats
│   ├── css/
│   │   └── style.css         # Dark theme, animations
│   └── js/
│       ├── app.js            # Point d'entrée, init, boucle principale
│       ├── ws.js             # Client WebSocket (connexion, envoi, réception)
│       ├── hologram.js       # Three.js — sphère d'énergie, particules, animations
│       ├── chat.js           # Interface chat (messages, input, envoi)
│       ├── notifications.js  # Affichage des notifications
│       └── voice.js          # Micro (MediaRecorder) → envoie audio au daemon
├── daemon/
│   ├── server/
│   │   ├── ws.py             # (EXISTANT — modifier pour servir aussi HTTP)
│   │   └── http.py           # Serveur HTTP pour le frontend (NEW)
│   └── voice/
│       ├── __init__.py       # (NEW)
│       ├── stt.py            # Whisper STT (NEW)
│       └── tts.py            # pyttsx3 TTS (NEW)
├── tests/
│   ├── test_voice.py         # (NEW)
│   └── test_frontend.py      # (NEW — vérifie que les fichiers existent)
```

---

### Task 1: Serveur HTTP pour le frontend

**Files:**
- Create: `daemon/server/http.py`
- Modify: `daemon/main.py` — lancer HTTP server en parallèle
- Create: `tests/test_http.py`

- [ ] **Step 1: Write test**

```python
# tests/test_http.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.server.http import FrontendServer

def test_server_creation():
    srv = FrontendServer(port=8080, frontend_dir="frontend")
    assert srv.port == 8080
    assert srv.frontend_dir == "frontend"
```

- [ ] **Step 2: Write http.py**

```python
# daemon/server/http.py
import os
import threading
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

logger = logging.getLogger("niambay.http")

class FrontendServer:
    def __init__(self, port=8080, frontend_dir="frontend"):
        self.port = port
        self.frontend_dir = str(Path(frontend_dir).resolve())
        self._server = None
        self._thread = None

    def start(self):
        root = self.frontend_dir
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=root, **kwargs)
            def log_message(self, format, *args):
                logger.debug(format % args)

        self._server = HTTPServer(("0.0.0.0", self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"Frontend: http://localhost:{self.port}")

    def stop(self):
        if self._server:
            self._server.shutdown()
```

- [ ] **Step 3: Run test, commit**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_http.py -v`
Commit: `git commit -m "feat: HTTP server for frontend"`

---

### Task 2: Frontend squelette — HTML + CSS + WebSocket

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/css/style.css`
- Create: `frontend/js/ws.js`
- Create: `frontend/js/app.js`
- Create: `tests/test_frontend.py`

- [ ] **Step 1: Write test**

```python
# tests/test_frontend.py
from pathlib import Path

def test_frontend_files_exist():
    base = Path("C:/niambay-v2/frontend")
    assert (base / "index.html").exists()
    assert (base / "css" / "style.css").exists()
    assert (base / "js" / "app.js").exists()
    assert (base / "js" / "ws.js").exists()

def test_index_html_has_required_elements():
    html = Path("C:/niambay-v2/frontend/index.html").read_text()
    assert "three.js" in html.lower() or "three" in html.lower()
    assert "ws.js" in html
    assert "app.js" in html
    assert "hologram" in html.lower()
```

- [ ] **Step 2: Create index.html**

Structure: container for hologram (canvas), chat panel (messages + input), stats bar, notification area. Load Three.js from CDN, load our JS files.

- [ ] **Step 3: Create style.css**

Dark theme (#0a0a1a background), glassmorphism panels, animations for hologram states (idle pulse, speaking glow, listening wave, thinking particles). Responsive.

- [ ] **Step 4: Create ws.js**

WebSocket client class: connect(url), send(type, data), onMessage callback, auto-reconnect on disconnect with exponential backoff.

- [ ] **Step 5: Create app.js**

Init: connect WebSocket, request status every 5s, handle incoming events (chat_response, event, notification, status). Wire up chat input.

- [ ] **Step 6: Run test, commit**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_frontend.py -v`
Commit: `git commit -m "feat: frontend skeleton — HTML + CSS + WebSocket"`

---

### Task 3: Hologramme 3D — Three.js

**Files:**
- Create: `frontend/js/hologram.js`

- [ ] **Step 1: Create hologram.js**

Three.js scene with:
- **Sphère d'énergie** — SphereGeometry avec wireframe + glow shader. Couleur bleu/cyan (#4a9eff).
- **Particules** — PointsMaterial, 200 particules orbitant la sphère. S'accélèrent quand thinking.
- **Animations par état:**
  - `idle` — pulse lent (scale 0.95-1.05, 4s), particules lentes
  - `speaking` — glow plus fort, sphère vibre rapidement, particules s'éloignent
  - `listening` — ondes concentriques (ring geometry s'expandant), couleur plus chaude
  - `thinking` — particules rapides en spirale, sphère tourne vite
  - `alert` — flash rouge momentané
- **API:** `hologram.setState(state)`, `hologram.resize()`, `hologram.init(container)`
- Responsive (resize avec la fenêtre)
- requestAnimationFrame loop

- [ ] **Step 2: Integrate into index.html**

Add `<script src="js/hologram.js"></script>` and init in app.js.

- [ ] **Step 3: Test visuellement**

Ouvrir `frontend/index.html` dans Chrome. Vérifier que la sphère apparaît et pulse.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: 3D hologram — Three.js energy sphere + particles"
```

---

### Task 4: Chat interface

**Files:**
- Create: `frontend/js/chat.js`

- [ ] **Step 1: Create chat.js**

Chat module:
- `chat.init(container, onSend)` — setup DOM (messages div, input, send button)
- `chat.addMessage(text, sender)` — add message bubble (user=right blue, bot=left green)
- `chat.setThinking(bool)` — show/hide "..." animation
- `chat.clear()`
- Enter key sends message
- Auto-scroll to bottom
- Timestamps on messages

- [ ] **Step 2: Wire into app.js**

On send: `ws.send("chat", {text})`. On receive chat_response: `chat.addMessage(text, "bot")`, change hologram to speaking, then back to idle.

- [ ] **Step 3: Test visuellement**

Ouvrir dans Chrome, taper un message, vérifier qu'il s'affiche (pas de réponse encore sans daemon).

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: chat interface"
```

---

### Task 5: Notifications frontend

**Files:**
- Create: `frontend/js/notifications.js`

- [ ] **Step 1: Create notifications.js**

- `notifications.init(container)` — setup DOM
- `notifications.show(title, message, level)` — toast popup (slide in from top-right, auto-dismiss after 5s)
- `notifications.badge(count)` — show unread count badge
- Level colors: info=blue, warning=orange, alert=red

- [ ] **Step 2: Wire into app.js**

On WS event type "notification": show toast + badge update.
On daemon alert events (high_cpu, disk_full, unpushed): show notification.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: frontend notifications — toasts + badge"
```

---

### Task 6: Voice — STT (Whisper) côté daemon

**Files:**
- Create: `daemon/voice/__init__.py`
- Create: `daemon/voice/stt.py`
- Create: `tests/test_voice.py`

- [ ] **Step 1: Write test**

```python
# tests/test_voice.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.voice.stt import SpeechToText

def test_stt_creation():
    stt = SpeechToText(model="base", language="fr")
    assert stt.model_name == "base"
    assert stt.language == "fr"
    assert stt.loaded == False

def test_stt_load():
    stt = SpeechToText(model="base")
    # Don't actually load (slow), just verify method exists
    assert hasattr(stt, 'load')
    assert hasattr(stt, 'transcribe_bytes')
```

- [ ] **Step 2: Write stt.py**

```python
# daemon/voice/stt.py
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger("niambay.stt")

class SpeechToText:
    def __init__(self, model="base", language="fr"):
        self.model_name = model
        self.language = language
        self._model = None
        self.loaded = False

    def load(self):
        import whisper
        logger.info(f"Loading Whisper model: {self.model_name}")
        self._model = whisper.load_model(self.model_name)
        self.loaded = True
        logger.info("Whisper ready")

    def transcribe_bytes(self, audio_bytes: bytes, sample_rate=16000) -> str:
        if not self.loaded:
            self.load()

        # Save to temp WAV
        import wave
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            tmp = f.name
            with wave.open(f, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)

        try:
            result = self._model.transcribe(tmp, language=self.language, fp16=False)
            text = result.get("text", "").strip()

            # Filter Whisper hallucinations
            garbage = {"sous-titres", "sous-titrage", "merci d'avoir regardé", "merci.", "...", "."}
            if text.lower() in garbage or len(text) < 3:
                return ""
            return text
        finally:
            Path(tmp).unlink(missing_ok=True)
```

- [ ] **Step 3: Run test, commit**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_voice.py -v`
Commit: `git commit -m "feat: STT — Whisper speech-to-text"`

---

### Task 7: Voice — TTS côté daemon

**Files:**
- Create: `daemon/voice/tts.py`
- Modify: `daemon/voice/__init__.py`
- Modify: `tests/test_voice.py`

- [ ] **Step 1: Write test**

```python
# Append to tests/test_voice.py
from daemon.voice.tts import TextToSpeech

def test_tts_creation():
    tts = TextToSpeech(language="fr", rate=160)
    assert tts.language == "fr"
    assert tts.rate == 160

def test_tts_has_speak():
    tts = TextToSpeech()
    assert hasattr(tts, 'speak')
    assert hasattr(tts, 'stop')
```

- [ ] **Step 2: Write tts.py**

```python
# daemon/voice/tts.py
import threading
import logging

logger = logging.getLogger("niambay.tts")

class TextToSpeech:
    def __init__(self, language="fr", rate=160, volume=0.9):
        self.language = language
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._speaking = False
        self._lock = threading.Lock()

    def _init_engine(self):
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
            voices = self._engine.getProperty('voices')
            for v in voices:
                if 'french' in v.name.lower() or 'fr' in v.id.lower():
                    self._engine.setProperty('voice', v.id)
                    break
            self._engine.setProperty('rate', self.rate)
            self._engine.setProperty('volume', self.volume)

    def speak(self, text: str):
        if not text or not text.strip():
            return
        with self._lock:
            self._speaking = True
            try:
                self._init_engine()
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")
            finally:
                self._speaking = False

    def speak_async(self, text: str):
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()

    @property
    def is_speaking(self):
        return self._speaking

    def stop(self):
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._speaking = False
```

- [ ] **Step 3: Create __init__.py**

```python
# daemon/voice/__init__.py
from .stt import SpeechToText
from .tts import TextToSpeech
```

- [ ] **Step 4: Run test, commit**

Run: `cd C:/niambay-v2 && python -m pytest tests/test_voice.py -v`
Commit: `git commit -m "feat: TTS — pyttsx3 text-to-speech"`

---

### Task 8: Voice frontend — micro dans Chrome

**Files:**
- Create: `frontend/js/voice.js`

- [ ] **Step 1: Create voice.js**

Uses browser MediaRecorder API (works in Chrome):
- `voice.init()` — request mic permission
- `voice.startListening()` — start recording audio chunks
- `voice.stopListening()` — stop, send audio via WebSocket as base64
- `voice.toggle()` — toggle listen/stop
- Visual indicator on hologram (listening state)
- VAD: detect silence after 2s, auto-stop and send

- [ ] **Step 2: Wire into app.js**

Add mic button in chat. On click: toggle recording. On audio received by daemon: transcribe (Whisper), respond (LLM), speak (TTS), send text + audio state back via WS.

- [ ] **Step 3: Wire into daemon main.py**

Handle WS message type "audio":
```python
elif msg_type == "audio":
    # base64 audio -> bytes -> Whisper -> text -> LLM -> TTS
    audio_b64 = msg.get("audio", "")
    audio_bytes = base64.b64decode(audio_b64)
    text = self.stt.transcribe_bytes(audio_bytes)
    if text:
        # Get LLM response
        response = self.llm.chat([LLMMessage("system", "..."), LLMMessage("user", text)])
        # Speak it
        self.tts.speak_async(response.content)
        return {"type": "voice_response", "transcription": text, "response": response.content}
```

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: voice — mic in Chrome + daemon STT/TTS pipeline"
```

---

### Task 9: Intégration finale — tout assembler

**Files:**
- Modify: `daemon/main.py` — add HTTP server, voice, hologram states
- Modify: `frontend/js/app.js` — wire everything

- [ ] **Step 1: Update daemon/main.py**

Add to __init__:
```python
from .server.http import FrontendServer
from .voice import SpeechToText, TextToSpeech
```

Init HTTP server, STT, TTS. Start HTTP server in run(). Handle audio messages.

- [ ] **Step 2: Update app.js**

Full wiring: WS events → hologram states, chat, notifications, voice. Status polling. Auto-reconnect.

- [ ] **Step 3: Test end-to-end**

1. `cd C:/niambay-v2 && python -m daemon.main`
2. Open `http://localhost:8080` in Chrome
3. Verify: hologram visible, chat works, notifications appear
4. Test voice if mic permissions granted

- [ ] **Step 4: Run all tests**

Run: `cd C:/niambay-v2 && python -m pytest tests/ -v`
Expected: ALL pass (60+)

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: Phase 3 complete — hologram + voice + full integration"
```

---

## Récapitulatif Phase 3

| Task | Composant | Type |
|------|-----------|------|
| 1 | HTTP Server | Backend |
| 2 | Frontend squelette | Frontend |
| 3 | Hologramme 3D | Frontend |
| 4 | Chat interface | Frontend |
| 5 | Notifications frontend | Frontend |
| 6 | STT (Whisper) | Backend |
| 7 | TTS (pyttsx3) | Backend |
| 8 | Voice frontend (micro Chrome) | Frontend + Backend |
| 9 | Intégration finale | Both |
| **Total** | **9 tasks** | |

Après Phase 3 : ouvrir Chrome → voir l'hologramme → lui parler → il répond à voix haute → notifications visuelles. Jarvis.
