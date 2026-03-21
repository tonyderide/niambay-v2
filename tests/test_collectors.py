import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.collectors.base import Collector, CollectorEvent
from daemon.collectors.window import WindowCollector
from daemon.collectors.process import ProcessCollector

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


def test_process_collector_collect():
    pc = ProcessCollector()
    events = pc.collect()
    assert isinstance(events, list)
    assert len(events) >= 1
    stats_evt = events[0]
    assert stats_evt.source == "process"
    assert stats_evt.event_type == "system_stats"
    assert "cpu_percent" in stats_evt.data
    assert "memory_percent" in stats_evt.data
    assert "disk_percent" in stats_evt.data
    assert "top_processes" in stats_evt.data
    assert len(stats_evt.data["top_processes"]) <= 10


def test_process_collector_detects_high_cpu():
    pc = ProcessCollector(cpu_threshold=0.0)
    events = pc.collect()
    alert_events = [e for e in events if e.event_type == "alert" and e.data.get("alert") == "high_cpu"]
    assert len(alert_events) >= 1
    assert alert_events[0].data["threshold"] == 0.0


from daemon.collectors.git import GitCollector

def test_git_collector():
    gc = GitCollector(watch_paths=["C:/niambay-v2"])
    assert isinstance(gc, Collector)
    events = gc.collect()
    assert isinstance(events, list)
    assert len(events) >= 1
    status_events = [e for e in events if e.event_type == "repo_status"]
    assert len(status_events) == 1
    evt = status_events[0]
    assert evt.source == "git"
    assert evt.data["branch"]  # should have a branch name
    assert "modified_files" in evt.data
    assert "last_commit" in evt.data
    assert "unpushed_commits" in evt.data
