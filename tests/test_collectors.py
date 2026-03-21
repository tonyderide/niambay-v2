import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.collectors.base import Collector, CollectorEvent
from daemon.collectors.window import WindowCollector

def test_collector_event():
    evt = CollectorEvent(source="window", event_type="app_change", data={"app": "Code.exe", "title": "main.py"}, timestamp=time.time())
    assert evt.source == "window"
    assert evt.data["app"] == "Code.exe"

def test_window_collector_is_collector():
    wc = WindowCollector()
    assert isinstance(wc, Collector)

def test_window_collector_collect():
    wc = WindowCollector()
    events = wc.collect()
    assert isinstance(events, list)
    if events:
        assert events[0].source == "window"
        assert "app" in events[0].data
        assert "title" in events[0].data
