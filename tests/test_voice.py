"""Tests for daemon.voice — STT and TTS wrappers."""

from daemon.voice.stt import SpeechToText
from daemon.voice.tts import TextToSpeech


def test_stt_creation():
    stt = SpeechToText(model="base", language="fr")
    assert stt.model_name == "base"
    assert stt.language == "fr"
    assert stt.loaded is False


def test_stt_has_methods():
    stt = SpeechToText()
    assert hasattr(stt, "load")
    assert hasattr(stt, "transcribe_bytes")


def test_tts_creation():
    tts = TextToSpeech(language="fr", rate=160)
    assert tts.language == "fr"
    assert tts.rate == 160


def test_tts_has_methods():
    tts = TextToSpeech()
    assert hasattr(tts, "speak")
    assert hasattr(tts, "stop")
    assert hasattr(tts, "speak_async")
