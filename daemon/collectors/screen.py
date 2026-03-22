import base64
import io
import time
import mss
from PIL import Image
from .base import Collector, CollectorEvent


class ScreenCollector(Collector):
    name = "screen"

    def __init__(self, interval: int = 30, resize_width: int = 800, vision_provider=None):
        self.interval = interval
        self.resize_width = resize_width
        self.vision_provider = vision_provider
        self._last_capture_time = 0

    def capture(self) -> tuple[bytes, int, int]:
        """Capture screen, resize, return (jpeg_bytes, width, height)."""
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # all monitors combined
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.rgb)

        # Resize maintaining aspect ratio
        ratio = self.resize_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((self.resize_width, new_height), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        jpeg_bytes = buf.getvalue()
        return jpeg_bytes, img.width, img.height

    def capture_base64(self) -> str:
        """Capture screen and return base64-encoded JPEG string."""
        jpeg_bytes, _, _ = self.capture()
        return base64.b64encode(jpeg_bytes).decode("ascii")

    def analyze(self, image_b64: str) -> str:
        """Analyze screenshot via vision provider if available."""
        if self.vision_provider and hasattr(self.vision_provider, "analyze_image"):
            return self.vision_provider.analyze_image(image_b64)
        return ""

    def collect(self) -> list[CollectorEvent]:
        """Capture screen if interval elapsed, return screen_analysis event."""
        events = []
        now = time.time()
        if now - self._last_capture_time < self.interval:
            return events

        try:
            image_b64 = self.capture_base64()
            self._last_capture_time = now

            analysis = self.analyze(image_b64)

            events.append(CollectorEvent(
                source="screen",
                event_type="screen_analysis",
                data={
                    "image_b64_length": len(image_b64),
                    "analysis": analysis,
                },
            ))
        except Exception:
            pass
        return events
