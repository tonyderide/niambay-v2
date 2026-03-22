"""Tests for daemon.brain.memory."""

from daemon.brain.memory import Memory, MemoryEvent


def test_memory_event():
    ev = MemoryEvent(source="cpu", event_type="spike", data={"value": 95})
    assert ev.source == "cpu"
    assert ev.event_type == "spike"
    assert ev.data == {"value": 95}
    assert ev.timestamp  # auto-generated, non-empty


def test_memory_store_and_recall():
    mem = Memory()
    mem.store(MemoryEvent(source="a", event_type="x", data={"i": 1}))
    mem.store(MemoryEvent(source="b", event_type="y", data={"i": 2}))
    last = mem.recent(1)
    assert len(last) == 1
    assert last[0].source == "b"  # most recent first


def test_memory_save_load(tmp_path):
    mem = Memory()
    mem.store(MemoryEvent(source="s", event_type="t", data={"k": "v"}))
    path = tmp_path / "mem.json"
    mem.save(path)
    mem2 = Memory.load(path)
    assert len(mem2.recent()) == 1
    assert mem2.recent()[0].data == {"k": "v"}


def test_memory_max_events():
    mem = Memory(max_events=5)
    for i in range(10):
        mem.store(MemoryEvent(source="s", event_type="t", data={"i": i}))
    assert len(mem.recent(100)) == 5
    # oldest kept should be i=5
    assert mem.recent(100)[-1].data == {"i": 5}


def test_memory_query_by_source():
    mem = Memory()
    mem.store(MemoryEvent(source="cpu", event_type="tick", data={}))
    mem.store(MemoryEvent(source="mem", event_type="tick", data={}))
    mem.store(MemoryEvent(source="cpu", event_type="tick", data={}))
    results = mem.query(source="cpu")
    assert len(results) == 2
    assert all(e.source == "cpu" for e in results)
