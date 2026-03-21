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
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            import psutil
            try:
                proc = psutil.Process(pid.value)
                app = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app = "unknown"

            if app != self._last_app or title != self._last_title:
                import time
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
