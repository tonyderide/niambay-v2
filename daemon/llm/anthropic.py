"""Anthropic LLM provider — Claude via REST API."""

import json
import time
import urllib.request
import urllib.error
from typing import List

from .base import LLMMessage, LLMResponse, LLMProvider


class AnthropicProvider(LLMProvider):
    """Talks to the Anthropic Messages API."""
    name = "anthropic"

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.timeout = 120

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        # Separate system message from the rest
        system_text = None
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_text = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        body: dict = {
            "model": kwargs.get("model", self.model),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "messages": chat_msgs,
        }
        if system_text:
            body["system"] = system_text

        payload = json.dumps(body).encode()

        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.API_VERSION,
            },
            method="POST",
        )

        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        latency = (time.monotonic() - t0) * 1000

        content = data["content"][0]["text"] if data.get("content") else ""
        usage = data.get("usage", {})
        tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            tokens_used=tokens,
            latency_ms=latency,
        )

    def is_available(self) -> bool:
        """Ping Anthropic — a keyless GET returns 401 but proves connectivity."""
        try:
            req = urllib.request.Request(self.API_URL, method="GET")
            urllib.request.urlopen(req, timeout=5)
            return True
        except urllib.error.HTTPError:
            # 401/405 means the API is reachable
            return True
        except (urllib.error.URLError, OSError):
            return False
