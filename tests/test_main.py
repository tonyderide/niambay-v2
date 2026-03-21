"""Tests for the main daemon assembly."""

import asyncio
import json

import pytest

from daemon.config import Config
from daemon.main import NiamBayDaemon


# ------------------------------------------------------------------
# Creation
# ------------------------------------------------------------------

def test_daemon_creation():
    cfg = Config(collect_interval=10)
    d = NiamBayDaemon(cfg)
    assert d.config.collect_interval == 10
    assert len(d.collectors) > 0


def test_daemon_default_config():
    d = NiamBayDaemon()
    assert d.config.ws_port == 8765
    assert d.running is False
    assert d.paused is False


def test_daemon_has_server():
    d = NiamBayDaemon()
    assert d.server is not None
    assert d.server.port == 8765


def test_daemon_has_task_executor():
    d = NiamBayDaemon()
    assert d.task_executor is not None


# ------------------------------------------------------------------
# Collection
# ------------------------------------------------------------------

def test_daemon_collect_once():
    cfg = Config()
    d = NiamBayDaemon(cfg)
    events = d.collect_all()
    assert isinstance(events, list)
    assert len(events) > 0


def test_daemon_collect_paused():
    cfg = Config(paused=True)
    d = NiamBayDaemon(cfg)
    events = d.collect_all()
    assert events == []


def test_daemon_pause_toggle():
    d = NiamBayDaemon()
    d.paused = True
    assert d.collect_all() == []
    d.paused = False
    assert len(d.collect_all()) > 0


# ------------------------------------------------------------------
# Git repo discovery
# ------------------------------------------------------------------

def test_find_git_repos():
    repos = NiamBayDaemon._find_git_repos()
    assert isinstance(repos, list)
    # At least niambay-v2 should be found (we're running inside it)
    assert any("niambay-v2" in r for r in repos)


# ------------------------------------------------------------------
# Client message handling
# ------------------------------------------------------------------

class FakeWebSocket:
    """Minimal fake for testing message handlers."""

    def __init__(self):
        self.sent: list[str] = []

    async def send(self, data: str):
        self.sent.append(data)


@pytest.mark.asyncio
async def test_handle_status():
    d = NiamBayDaemon()
    ws = FakeWebSocket()
    await d._handle_client_message(ws, {"type": "status"})
    assert len(ws.sent) == 1
    payload = json.loads(ws.sent[0])
    assert payload["type"] == "status"
    assert "paused" in payload["data"]


@pytest.mark.asyncio
async def test_handle_pause():
    d = NiamBayDaemon()
    ws = FakeWebSocket()
    await d._handle_client_message(ws, {"type": "pause", "paused": True})
    assert d.paused is True
    payload = json.loads(ws.sent[0])
    assert payload["type"] == "pause"
    assert payload["data"]["paused"] is True


@pytest.mark.asyncio
async def test_handle_unknown_type():
    d = NiamBayDaemon()
    ws = FakeWebSocket()
    await d._handle_client_message(ws, {"type": "foobar"})
    payload = json.loads(ws.sent[0])
    assert payload["type"] == "error"


@pytest.mark.asyncio
async def test_handle_chat_no_llm():
    d = NiamBayDaemon()
    d.llm_provider = None
    ws = FakeWebSocket()
    await d._handle_client_message(ws, {"type": "chat", "text": "hello"})
    payload = json.loads(ws.sent[0])
    assert payload["type"] == "error"
    assert "LLM" in payload["data"]["message"]


@pytest.mark.asyncio
async def test_handle_task_no_llm():
    d = NiamBayDaemon()
    d.llm_provider = None
    ws = FakeWebSocket()
    await d._handle_client_message(ws, {"type": "task", "task_type": "analyze", "description": "test"})
    payload = json.loads(ws.sent[0])
    assert payload["type"] == "error"


# ------------------------------------------------------------------
# Stop
# ------------------------------------------------------------------

def test_daemon_stop():
    d = NiamBayDaemon()
    d.running = True
    d.stop()
    assert d.running is False
