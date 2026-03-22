"""Multi-LLM adapter — factory for provider instances."""

from .base import LLMMessage, LLMResponse, LLMProvider
from .ollama import OllamaProvider
from .anthropic import AnthropicProvider
from .groq import GroqProvider
from .google import GoogleProvider
from .cascade import CascadeProvider
from .sambanova import SambaNovaProvider


def create_provider(provider: str, **kwargs) -> LLMProvider:
    """Return an LLMProvider instance for the given provider name.

    Args:
        provider: "ollama", "anthropic", "groq", "google", or "cascade"
        **kwargs: forwarded to the provider constructor
    """
    providers = {
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
        "google": GoogleProvider,
        "cascade": CascadeProvider,
        "sambanova": SambaNovaProvider,
    }
    cls = providers.get(provider)
    if cls is None:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(providers)}")
    return cls(**kwargs)


def create_cascade(config) -> CascadeProvider:
    """Create a cascade of all available providers."""
    providers = []

    # Groq first (free, fast, best quality for free)
    if getattr(config, 'groq_api_key', ''):
        providers.append(GroqProvider(api_key=config.groq_api_key))

    # Gemini (free, good quality, backup)
    if getattr(config, 'gemini_api_key', ''):
        providers.append(GoogleProvider(api_key=config.gemini_api_key))

    # Anthropic (paid, best quality)
    if getattr(config, 'llm_api_key', '') and config.llm_provider == 'anthropic':
        providers.append(AnthropicProvider(api_key=config.llm_api_key))

    # Ollama last (local, free, but lower quality)
    try:
        ollama = OllamaProvider(url=config.llm_url, model=config.llm_model)
        if ollama.is_available():
            providers.append(ollama)
    except Exception:
        pass

    return CascadeProvider(providers)
