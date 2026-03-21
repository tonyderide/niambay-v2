"""Ollama LLM provider — local models via REST API."""

import json
import time
import urllib.request
import urllib.error
from typing import List

from .base import LLMMessage, LLMResponse, LLMProvider


class OllamaProvider(LLMProvider):
    """Talks to a local Ollama instance."""

    def __init__(self, url: str = "http://localhost:11434", model: str = "llama3"):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = 120

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        payload = json.dumps({
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            f"{self.url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read())
        latency = (time.monotonic() - t0) * 1000

        return LLMResponse(
            content=body["message"]["content"],
            model=body.get("model", self.model),
            tokens_used=body.get("eval_count", 0),
            latency_ms=latency,
        )

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except (urllib.error.URLError, OSError):
            return False
