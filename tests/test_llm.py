"""Tests for the multi-LLM adapter layer."""

from daemon.llm.base import LLMMessage, LLMResponse, LLMProvider


def test_llm_message():
    msg = LLMMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_llm_response():
    resp = LLMResponse(content="hi", model="test-model", tokens_used=42, latency_ms=123.4)
    assert resp.content == "hi"
    assert resp.model == "test-model"
    assert resp.tokens_used == 42
    assert resp.latency_ms == 123.4


def test_provider_interface():
    assert hasattr(LLMProvider, "chat")
    assert hasattr(LLMProvider, "is_available")
    assert callable(getattr(LLMProvider, "chat"))
    assert callable(getattr(LLMProvider, "is_available"))
