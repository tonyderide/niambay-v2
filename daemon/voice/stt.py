"""Speech-to-Text via OpenAI Whisper."""

import io
import struct
import tempfile
import os


class SpeechToText:
    """Transcribe audio bytes to text using Whisper."""

    # Short garbage strings Whisper hallucinates on silence
    _GARBAGE = {
        "", " ", ".", "...", "you", "thank you", "thanks",
        "merci", "sous-titres", "sous-titrage",
        "sous-titres réalisés para la communauté d'amara.org",
    }

    def __init__(self, model: str = "base", language: str = "fr"):
        self.model_name = model
        self.language = language
        self.loaded = False
        self._model = None

    def load(self):
        """Load the Whisper model (lazy, call once)."""
        import whisper  # noqa: delayed import

        self._model = whisper.load_model(self.model_name)
        self.loaded = True

    def transcribe_bytes(
        self, audio_bytes: bytes, sample_rate: int = 16000
    ) -> str:
        """Transcribe raw 16-bit mono PCM bytes to text.

        Returns empty string on silence / garbage.
        """
        if not self.loaded:
            self.load()

        # Write a minimal WAV so Whisper can open it
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            n_samples = len(audio_bytes) // 2
            # WAV header (16-bit mono PCM)
            tmp.write(b"RIFF")
            data_size = 36 + len(audio_bytes)
            tmp.write(struct.pack("<I", data_size))
            tmp.write(b"WAVE")
            tmp.write(b"fmt ")
            tmp.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate,
                                  sample_rate * 2, 2, 16))
            tmp.write(b"data")
            tmp.write(struct.pack("<I", len(audio_bytes)))
            tmp.write(audio_bytes)
            tmp.close()

            result = self._model.transcribe(
                tmp.name,
                language=self.language,
                fp16=False,
            )
            text = result.get("text", "").strip()
        finally:
            os.unlink(tmp.name)

        if text.lower() in self._GARBAGE:
            return ""
        return text
