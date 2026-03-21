"""Base classes for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str       # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    tokens_used: int
    latency_ms: float


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Send messages and get a response."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is reachable."""
        ...
