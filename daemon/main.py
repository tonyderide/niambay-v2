"""Main daemon — assembles collectors, WebSocket server, LLM, and task executor."""

import asyncio
import json
import logging
import os
import signal
import sys
from dataclasses import asdict
from pathlib import Path

from daemon.config import Config
from daemon.collectors import WindowCollector, ProcessCollector, GitCollector
from daemon.collectors.base import CollectorEvent
from daemon.llm import create_provider, create_cascade
from daemon.llm.base import LLMMessage
from daemon.server.http import FrontendServer
from daemon.server.ws import NiamBayServer
from daemon.tasks.executor import TaskExecutor, Task
from daemon.brain import Memory, MemoryEvent, HabitTracker
from daemon.notifications import NotificationManager
from daemon.voice import SpeechToText, TextToSpeech
from daemon.prompts import SYSTEM_PROMPT

logger = logging.getLogger("niambay")

DEFAULT_GIT_PATHS = ["C:/niambay-v2", "C:/niam-bay", "C:/martin"]


class NiamBayDaemon:
    """Ties together collectors, WebSocket server, LLM provider, and task executor."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.running = False
        self.paused = self.config.paused

        # --- Collectors ---
        git_repos = self._find_git_repos()
        self.collectors = [
            WindowCollector(),
            ProcessCollector(),
            GitCollector(watch_paths=git_repos),
        ]

        # --- WebSocket server ---
        self.server = NiamBayServer(
            host=self.config.ws_host,
            port=self.config.ws_port,
        )
        self.server.on_message(self._handle_client_message)

        # --- LLM provider (optional — daemon works without it) ---
        self.llm_provider = self._create_llm_provider()

        # --- Task executor ---
        self.task_executor = TaskExecutor()

        # --- Brain + Notifications ---
        self.memory = Memory()
        self.habits = HabitTracker()
        self.notifier = NotificationManager()

        # --- HTTP server (serves frontend) ---
        frontend_dir = str(Path(__file__).parent.parent / "frontend")
        self.http_server = FrontendServer(port=8080, frontend_dir=frontend_dir)

        # --- Voice (lazy-loaded, optional) ---
        self.stt = SpeechToText()
        self.tts = TextToSpeech()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_git_repos() -> list[str]:
        """Return paths from DEFAULT_GIT_PATHS that contain a .git directory."""
        repos = []
        for p in DEFAULT_GIT_PATHS:
            if Path(p, ".git").is_dir():
                repos.append(p)
        return repos

    def _create_llm_provider(self):
        """Try to create the configured LLM provider; return None on failure."""
        try:
            # Use cascade by default — tries all available providers in order
            if self.config.use_cascade:
                cascade = create_cascade(self.config)
                if cascade.is_available():
                    return cascade
                logger.warning("Cascade has no available providers — falling back to single provider")

            provider_name = self.config.llm_provider
            kwargs: dict = {"model": self.config.llm_model}

            if provider_name == "ollama":
                kwargs["url"] = self.config.llm_url
            elif provider_name == "anthropic":
                api_key = self.config.llm_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
                if not api_key:
                    logger.warning("No Anthropic API key — LLM disabled")
                    return None
                kwargs["api_key"] = api_key
            elif provider_name == "groq":
                kwargs["api_key"] = self.config.groq_api_key
            elif provider_name == "google":
                kwargs["api_key"] = self.config.gemini_api_key
            else:
                kwargs["url"] = self.config.llm_url  # fallback

            return create_provider(provider_name, **kwargs)
        except Exception as exc:
            logger.warning("Could not create LLM provider: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def collect_all(self) -> list[CollectorEvent]:
        """Run every collector and return the merged event list.  Empty if paused."""
        if self.paused:
            return []
        events: list[CollectorEvent] = []
        for collector in self.collectors:
            try:
                events.extend(collector.collect())
            except Exception as exc:
                logger.error("Collector %s failed: %s", getattr(collector, "name", "?"), exc)

        import time as _time
        for evt in events:
            # Store in memory
            self.memory.store(MemoryEvent(source=evt.source, event_type=evt.event_type, data=evt.data))
            # Record habits
            if evt.event_type == "app_change":
                hour = _time.localtime().tm_hour
                self.habits.record("app_usage", evt.data.get("app", "unknown"), hour=hour)
            # Auto-notify on alerts
            if evt.event_type in ("high_cpu", "high_memory", "disk_full"):
                self.notifier.notify(f"Alerte {evt.event_type}", str(evt.data), level="warning")
            if evt.event_type == "unpushed_alert":
                self.notifier.notify("Git non pushé", f"{evt.data.get('repo')}: {evt.data.get('count')} commits", level="info")

        return events

    # ------------------------------------------------------------------
    # Client message handling
    # ------------------------------------------------------------------

    async def _handle_client_message(self, websocket, msg: dict):
        """Dispatch a message from a WebSocket client."""
        msg_type = msg.get("type", "")

        if msg_type == "chat":
            await self._handle_chat(websocket, msg)
        elif msg_type == "task":
            await self._handle_task(websocket, msg)
        elif msg_type == "status":
            await self._handle_status(websocket)
        elif msg_type == "pause":
            await self._handle_pause(websocket, msg)
        elif msg_type == "audio":
            await self._handle_audio(websocket, msg)
        elif msg_type == "notifications":
            await self._handle_notifications(websocket)
        elif msg_type == "config_get":
            await self._handle_config_get(websocket)
        elif msg_type == "config_set":
            await self._handle_config_set(websocket, msg)
        elif msg_type == "test_llm":
            await self._handle_test_llm(websocket)
        elif msg_type == "clear_memory":
            await self._handle_clear_memory(websocket)
        else:
            await websocket.send(
                NiamBayServer.format_event("error", {"message": f"Unknown type: {msg_type}"})
            )

    async def _handle_chat(self, websocket, msg: dict):
        if not self.llm_provider:
            await websocket.send(
                NiamBayServer.format_event("error", {"message": "LLM not available"})
            )
            return
        text = msg.get("text", "")
        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=text),
        ]
        try:
            response = self.llm_provider.chat(messages)
            await websocket.send(
                NiamBayServer.format_event("chat_response", {
                    "text": response.content,
                    "model": response.model,
                    "tokens": response.tokens_used,
                    "latency_ms": response.latency_ms,
                })
            )
        except Exception as exc:
            await websocket.send(
                NiamBayServer.format_event("error", {"message": f"LLM error: {exc}"})
            )

    async def _handle_audio(self, websocket, msg: dict):
        """Transcribe incoming audio and optionally respond via LLM + TTS."""
        import base64

        audio_b64 = msg.get("audio", "")
        audio_bytes = base64.b64decode(audio_b64)

        # Transcribe
        text = self.stt.transcribe_bytes(audio_bytes)

        if text and self.llm_provider:
            messages = [
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=text),
            ]
            try:
                response = self.llm_provider.chat(messages)
                # Speak response asynchronously
                self.tts.speak_async(response.content)
                await websocket.send(
                    NiamBayServer.format_event("voice_response", {
                        "transcription": text,
                        "response": response.content,
                    })
                )
            except Exception as exc:
                await websocket.send(
                    NiamBayServer.format_event("error", {"message": f"Voice LLM error: {exc}"})
                )
        else:
            await websocket.send(
                NiamBayServer.format_event("voice_response", {
                    "transcription": text or "",
                    "response": "",
                })
            )

    async def _handle_task(self, websocket, msg: dict):
        if not self.llm_provider:
            await websocket.send(
                NiamBayServer.format_event("error", {"message": "LLM not available"})
            )
            return
        task = Task(
            type=msg.get("task_type", "analyze"),
            description=msg.get("description", ""),
            context=msg.get("context", {}),
        )
        try:
            result = await self.task_executor.execute(task, self.llm_provider)
            await websocket.send(
                NiamBayServer.format_event("task_result", {
                    "type": result.type,
                    "description": result.description,
                    "result": result.result,
                })
            )
        except Exception as exc:
            await websocket.send(
                NiamBayServer.format_event("error", {"message": f"Task error: {exc}"})
            )

    async def _handle_notifications(self, websocket):
        items = [
            {"title": n.title, "message": n.message, "level": n.level, "id": n.id, "read": n.read}
            for n in self.notifier.pending()
        ]
        await websocket.send(
            NiamBayServer.format_event("notifications", {"type": "notifications", "items": items})
        )

    async def _handle_status(self, websocket):
        status = {
            "paused": self.paused,
            "collectors": [c.name for c in self.collectors],
            "llm_available": self.llm_provider is not None,
            "llm_provider": self.config.llm_provider,
            "clients_connected": len(self.server.clients),
            "config": asdict(self.config),
            "memory_events": len(self.memory._events),
            "habits_detected": len(self.habits.detect()),
            "notifications_pending": len(self.notifier.pending()),
        }
        await websocket.send(NiamBayServer.format_event("status", status))

    async def _handle_pause(self, websocket, msg: dict):
        self.paused = msg.get("paused", not self.paused)
        await websocket.send(
            NiamBayServer.format_event("pause", {"paused": self.paused})
        )

    # ------------------------------------------------------------------
    # Config handlers
    # ------------------------------------------------------------------

    async def _handle_config_get(self, websocket):
        """Return full config as JSON."""
        await websocket.send(
            NiamBayServer.format_event("config", asdict(self.config))
        )

    async def _handle_config_set(self, websocket, msg: dict):
        """Update config fields, persist, and apply live changes."""
        data = msg.get("data", {})
        for key, value in data.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Persist to disk
        config_path = Path.home() / ".niambay" / "config.json"
        self.config.save(str(config_path))

        # Apply live changes: LLM provider
        if any(k in data for k in ("llm_provider", "llm_model", "llm_url", "llm_api_key", "groq_api_key", "gemini_api_key", "use_cascade")):
            try:
                self.llm_provider = self._create_llm_provider()
                logger.info("LLM provider reloaded: %s / %s", self.config.llm_provider, self.config.llm_model)
            except Exception as exc:
                logger.warning("Failed to reload LLM provider: %s", exc)

        # Apply live changes: paused state
        if "paused" in data or "do_not_observe" in data:
            self.paused = self.config.paused or self.config.do_not_observe

        await websocket.send(
            NiamBayServer.format_event("config", asdict(self.config))
        )

    async def _handle_test_llm(self, websocket):
        """Send a test message to the LLM and return the result."""
        if not self.llm_provider:
            await websocket.send(
                NiamBayServer.format_event("test_llm_result", {
                    "success": False,
                    "message": "LLM provider not configured or unavailable",
                })
            )
            return
        try:
            response = self.llm_provider.chat([
                LLMMessage(role="user", content="Dis simplement 'OK' pour confirmer que tu fonctionnes.")
            ])
            await websocket.send(
                NiamBayServer.format_event("test_llm_result", {
                    "success": True,
                    "message": response.content,
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                })
            )
        except Exception as exc:
            await websocket.send(
                NiamBayServer.format_event("test_llm_result", {
                    "success": False,
                    "message": str(exc),
                })
            )

    async def _handle_clear_memory(self, websocket):
        """Clear all brain memory events."""
        self.memory._events.clear()
        await websocket.send(
            NiamBayServer.format_event("clear_memory_result", {"success": True, "message": "Memory cleared"})
        )

    # ------------------------------------------------------------------
    # Main loops
    # ------------------------------------------------------------------

    async def _collection_loop(self):
        """Periodically collect events and broadcast them."""
        while self.running:
            events = self.collect_all()
            for event in events:
                await self.server.broadcast(event.source, {
                    "event_type": event.event_type,
                    "data": event.data,
                    "timestamp": event.timestamp,
                })
            await asyncio.sleep(self.config.collect_interval)

    async def run(self):
        """Start HTTP server, WebSocket server and collection loop."""
        self.running = True

        # Start HTTP server in a daemon thread (non-blocking)
        self.http_server.start()
        logger.info("Frontend HTTP server on http://localhost:%d", self.http_server.port)

        logger.info(
            "Niam-Bay daemon starting — ws://%s:%d — interval %.1fs",
            self.config.ws_host, self.config.ws_port, self.config.collect_interval,
        )
        await asyncio.gather(
            self.server.start(),
            self._collection_loop(),
        )

    def stop(self):
        """Signal the daemon to stop."""
        self.running = False
        self.http_server.stop()
        logger.info("Niam-Bay daemon stopping")


# ======================================================================
# Entry point
# ======================================================================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    )

    config_path = Path.home() / ".niambay" / "config.json"
    if config_path.exists():
        config = Config.load(str(config_path))
        logger.info("Loaded config from %s", config_path)
    else:
        config = Config()
        logger.info("Using default config")

    daemon = NiamBayDaemon(config)

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.new_event_loop()

    def _shutdown(sig, frame):
        daemon.stop()
        loop.call_soon_threadsafe(loop.stop)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(daemon.run())
    except (KeyboardInterrupt, SystemExit):
        daemon.stop()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
