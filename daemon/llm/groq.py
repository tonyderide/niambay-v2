# daemon/llm/groq.py
import json
import time
import urllib.request
from .base import LLMProvider, LLMMessage, LLMResponse


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key="", model="llama-3.1-70b-versatile", **kwargs):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        start = time.time()
        payload = json.dumps({
            "model": kwargs.get("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.7),
        }).encode()

        req = urllib.request.Request(self.url, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        })
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        tokens = data.get("usage", {}).get("total_tokens", 0)
        latency = int((time.time() - start) * 1000)

        return LLMResponse(content=content, model=self.model, tokens_used=tokens, latency_ms=latency)

    def is_available(self) -> bool:
        return bool(self.api_key)
