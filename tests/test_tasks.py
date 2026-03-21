"""Tests for the task executor module."""

from daemon.tasks import Task, TaskExecutor


def test_task_creation():
    """Create a Task and verify all fields."""
    task = Task(
        type="analyze",
        description="Check memory usage",
        context={"source": "collector", "period": "24h"},
    )
    assert task.type == "analyze"
    assert task.description == "Check memory usage"
    assert task.context == {"source": "collector", "period": "24h"}
    assert task.result is None


def test_executor_build_prompt():
    """Build a prompt and verify it contains description + context."""
    executor = TaskExecutor()
    task = Task(
        type="summarize",
        description="Daily report",
        context={"date": "2026-03-21", "mood": "calm"},
    )
    prompt = executor._build_prompt(task)
    assert "Daily report" in prompt
    assert "date: 2026-03-21" in prompt
    assert "mood: calm" in prompt
