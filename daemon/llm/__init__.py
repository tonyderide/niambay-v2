"""Multi-LLM adapter — factory for provider instances."""

from .base import LLMMessage, LLMResponse, LLMProvider
from .ollama import OllamaProvider
from .anthropic import AnthropicProvider


def create_provider(provider: str, **kwargs) -> LLMProvider:
    """Return an LLMProvider instance for the given provider name.

    Args:
        provider: "ollama" or "anthropic"
        **kwargs: forwarded to the provider constructor
    """
    providers = {
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
    }
    cls = providers.get(provider)
    if cls is None:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(providers)}")
    return cls(**kwargs)
