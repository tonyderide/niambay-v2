# daemon/llm/google.py
import json
import time
import urllib.request
from .base import LLMProvider, LLMMessage, LLMResponse


class GoogleProvider(LLMProvider):
    name = "google"

    def __init__(self, api_key="", model="gemini-2.0-flash", **kwargs):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        start = time.time()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        # Convert messages to Gemini format
        system = ""
        contents = []
        for m in messages:
            if m.role == "system":
                system = m.content
            elif m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.content}]})

        body = {"contents": contents}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        payload = json.dumps(body).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())

        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                content = parts[0].get("text", "")

        tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        latency = int((time.time() - start) * 1000)

        return LLMResponse(content=content, model=self.model, tokens_used=tokens, latency_ms=latency)

    def is_available(self) -> bool:
        return bool(self.api_key)
