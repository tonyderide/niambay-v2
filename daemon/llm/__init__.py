"""Multi-LLM adapter — factory for provider instances."""

from .base import LLMMessage, LLMResponse, LLMProvider
from .ollama import OllamaProvider
from .anthropic import AnthropicProvider
from .groq import GroqProvider
from .google import GoogleProvider
from .cascade import CascadeProvider
from .sambanova import SambaNovaProvider
from .mistral import MistralProvider
from .cerebras import CerebrasProvider


def create_provider(provider: str, **kwargs) -> LLMProvider:
    """Return an LLMProvider instance for the given provider name.

    Args:
        provider: "ollama", "anthropic", "groq", "google", "cascade",
                  "sambanova", "mistral", or "cerebras"
        **kwargs: forwarded to the provider constructor
    """
    providers = {
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
        "google": GoogleProvider,
        "cascade": CascadeProvider,
        "sambanova": SambaNovaProvider,
        "mistral": MistralProvider,
        "cerebras": CerebrasProvider,
    }
    cls = providers.get(provider)
    if cls is None:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(providers)}")
    return cls(**kwargs)


def create_cascade(config) -> CascadeProvider:
    """Create a cascade of all available free providers.

    Order (best free first):
    1. Mistral   — 1B tokens/month free, works from PC
    2. SambaNova — DeepSeek V3, works from PC, rate limited
    3. Cerebras  — fast inference, works from VM only (Cloudflare blocks PC)
    4. Google    — Gemini, rate limited
    5. Groq      — rate limited
    6. Anthropic  — paid, best quality (only if configured)
    7. Ollama    — local fallback
    """
    providers = []

    # 1. Mistral (1B tokens/month free, works from PC)
    if getattr(config, 'mistral_api_key', ''):
        providers.append(MistralProvider(api_key=config.mistral_api_key))

    # 2. SambaNova (DeepSeek V3, works from PC)
    if getattr(config, 'sambanova_api_key', ''):
        providers.append(SambaNovaProvider(api_key=config.sambanova_api_key))

    # 3. Cerebras (fast, VM only — Cloudflare blocks PC)
    if getattr(config, 'cerebras_api_key', ''):
        providers.append(CerebrasProvider(api_key=config.cerebras_api_key))

    # 4. Google Gemini (rate limited)
    if getattr(config, 'gemini_api_key', ''):
        providers.append(GoogleProvider(api_key=config.gemini_api_key))

    # 5. Groq (rate limited)
    if getattr(config, 'groq_api_key', ''):
        providers.append(GroqProvider(api_key=config.groq_api_key))

    # 6. Anthropic (paid, only if explicitly configured)
    if getattr(config, 'llm_api_key', '') and getattr(config, 'llm_provider', '') == 'anthropic':
        providers.append(AnthropicProvider(api_key=config.llm_api_key))

    # 7. Ollama (local fallback)
    try:
        ollama = OllamaProvider(url=config.llm_url, model=config.llm_model)
        if ollama.is_available():
            providers.append(ollama)
    except Exception:
        pass

    return CascadeProvider(providers)
