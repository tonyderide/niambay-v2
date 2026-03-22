# daemon/llm/cascade.py
import logging
from .base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger("niambay.llm.cascade")


class CascadeProvider(LLMProvider):
    """Try providers in order. If one fails, try the next."""
    name = "cascade"

    def __init__(self, providers: list[LLMProvider]):
        self.providers = [p for p in providers if p.is_available()]
        logger.info(f"Cascade LLM: {[p.name for p in self.providers]}")

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        last_error = None
        for provider in self.providers:
            try:
                response = provider.chat(messages, **kwargs)
                if response.content:
                    logger.debug(f"Cascade: {provider.name} responded ({response.latency_ms}ms)")
                    return response
            except Exception as e:
                logger.warning(f"Cascade: {provider.name} failed: {e}")
                last_error = e
                continue

        # All failed
        error_msg = f"All providers failed. Last error: {last_error}" if last_error else "No providers available"
        return LLMResponse(content=f"Erreur: {error_msg}", model="cascade", tokens_used=0, latency_ms=0)

    def is_available(self) -> bool:
        return len(self.providers) > 0
