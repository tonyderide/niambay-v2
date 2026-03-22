import base64
import pytest
from unittest.mock import patch, MagicMock
from daemon.collectors.screen import ScreenCollector


def _make_fake_sct():
    """Create a fake mss instance with grab() returning a fake screenshot."""
    from PIL import Image
    img = Image.new("RGB", (100, 60), color=(255, 0, 0))
    raw_bytes = img.tobytes()

    class FakeScreenshot:
        size = img.size
        rgb = raw_bytes

    fake_sct = MagicMock()
    fake_sct.monitors = [{"top": 0, "left": 0, "width": 100, "height": 60}]
    fake_sct.grab.return_value = FakeScreenshot()
    fake_sct.__enter__ = MagicMock(return_value=fake_sct)
    fake_sct.__exit__ = MagicMock(return_value=False)
    return fake_sct


def test_screen_collector_creation():
    sc = ScreenCollector(interval=10, resize_width=640)
    assert sc.interval == 10
    assert sc.resize_width == 640
    assert sc.vision_provider is None
    assert sc.name == "screen"


@patch("daemon.collectors.screen.mss.mss")
def test_screen_capture_returns_bytes(mock_mss):
    mock_mss.return_value = _make_fake_sct()
    sc = ScreenCollector(resize_width=800)
    jpeg_bytes, w, h = sc.capture()
    assert isinstance(jpeg_bytes, bytes)
    assert len(jpeg_bytes) > 0
    # Should be valid JPEG (starts with FFD8)
    assert jpeg_bytes[:2] == b'\xff\xd8'
    assert isinstance(w, int)
    assert isinstance(h, int)


@patch("daemon.collectors.screen.mss.mss")
def test_screen_capture_resize(mock_mss):
    mock_mss.return_value = _make_fake_sct()
    sc = ScreenCollector(resize_width=400)
    jpeg_bytes, w, h = sc.capture()
    assert w == 400
    # Original is 100x60, ratio = 4.0, so height = 240
    assert h == 240


@patch("daemon.collectors.screen.mss.mss")
def test_screen_to_base64(mock_mss):
    mock_mss.return_value = _make_fake_sct()
    sc = ScreenCollector(resize_width=800)
    b64 = sc.capture_base64()
    assert isinstance(b64, str)
    # Should be valid base64 that decodes to JPEG
    decoded = base64.b64decode(b64)
    assert decoded[:2] == b'\xff\xd8'
