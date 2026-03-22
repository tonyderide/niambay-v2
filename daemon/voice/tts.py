"""Text-to-Speech via pyttsx3."""

import threading


class TextToSpeech:
    """Speak text aloud using pyttsx3 (offline, cross-platform)."""

    def __init__(self, language: str = "fr", rate: int = 160, volume: float = 0.9):
        self.language = language
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._lock = threading.Lock()
        self._speaking = False

    # --- lazy init -------------------------------------------------------

    def _init_engine(self):
        """Create pyttsx3 engine and pick a French voice if available."""
        import pyttsx3  # noqa: delayed import

        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)

        # Try to find a voice whose id/name contains the language tag
        for voice in engine.getProperty("voices"):
            vid = (voice.id + voice.name).lower()
            if self.language in vid:
                engine.setProperty("voice", voice.id)
                break

        self._engine = engine

    # --- public API ------------------------------------------------------

    def speak(self, text: str):
        """Speak *text* synchronously (thread-safe)."""
        with self._lock:
            if self._engine is None:
                self._init_engine()
            self._speaking = True
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            finally:
                self._speaking = False

    def speak_async(self, text: str):
        """Fire-and-forget: speak in a daemon thread."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self):
        """Stop current speech if engine exists."""
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception:
                    pass
            self._speaking = False
