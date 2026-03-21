"""Tests for the WebSocket server."""

import json

from daemon.server import NiamBayServer


def test_server_creation():
    """Verify host, port, and empty clients on creation."""
    server = NiamBayServer(host="0.0.0.0", port=9000)
    assert server.host == "0.0.0.0"
    assert server.port == 9000
    assert server.clients == set()


def test_server_format_event():
    """Verify JSON format with type, data, and timestamp."""
    event_json = NiamBayServer.format_event("test_event", {"key": "value"})
    event = json.loads(event_json)
    assert event["type"] == "test_event"
    assert event["data"] == {"key": "value"}
    assert "timestamp" in event
    # Timestamp should be a valid ISO format string
    assert "T" in event["timestamp"]
