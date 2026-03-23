from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from .base import Collector, CollectorEvent
import threading


class FilesystemCollector(Collector):
    name = "filesystem"

    def __init__(self, watch_paths=None):
        self.watch_paths = watch_paths or [str(Path.home())]
        self._events = []
        self._lock = threading.Lock()
        self._observer = None
        self._start_watching()

    def _start_watching(self):
        handler = _ChangeHandler(self._events, self._lock)
        self._observer = Observer()
        for path in self.watch_paths:
            if Path(path).exists():
                self._observer.schedule(handler, path, recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def collect(self) -> list[CollectorEvent]:
        with self._lock:
            events = list(self._events)
            self._events.clear()
        return events

    def cleanup(self):
        if self._observer:
            self._observer.stop()


class _ChangeHandler(FileSystemEventHandler):
    def __init__(self, events, lock):
        self._events = events
        self._lock = lock

    def on_modified(self, event):
        if event.is_directory:
            return
        with self._lock:
            self._events.append(CollectorEvent(
                source="filesystem",
                event_type="file_modified",
                data={"path": event.src_path, "type": "modified"}
            ))

    def on_created(self, event):
        if event.is_directory:
            return
        with self._lock:
            self._events.append(CollectorEvent(
                source="filesystem",
                event_type="file_created",
                data={"path": event.src_path, "type": "created"}
            ))

    def on_deleted(self, event):
        if event.is_directory:
            return
        with self._lock:
            self._events.append(CollectorEvent(
                source="filesystem",
                event_type="file_deleted",
                data={"path": event.src_path, "type": "deleted"}
            ))
