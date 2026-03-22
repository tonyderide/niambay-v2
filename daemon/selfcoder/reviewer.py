"""SelfCoder Reviewer — sends diffs to Mistral for code review."""

from daemon.llm.base import LLMMessage, LLMProvider


REVIEW_PROMPT = """You are a strict code reviewer for the Niam-Bay project.
Review the following git diff. Check for:
- Syntax errors
- Security issues (secrets, dangerous calls)
- Logic bugs
- Style problems

Respond with exactly one word on the first line: APPROVE or REJECT
Then explain your reasoning on subsequent lines."""


class Reviewer:
    """Reviews code diffs using an LLM (typically Mistral)."""

    def __init__(self, provider: LLMProvider, model: str = "mistral-small-latest"):
        self.provider = provider
        self.model = model

    def review_diff(self, diff: str) -> tuple[bool, str]:
        """Send a git diff to the LLM for review.

        Returns:
            (approved, explanation) — True if APPROVE, False if REJECT.
        """
        messages = [
            LLMMessage(role="system", content=REVIEW_PROMPT),
            LLMMessage(role="user", content=diff),
        ]
        response = self.provider.chat(messages, model=self.model)
        approved = self.parse_verdict(response.content)
        return approved, response.content

    @staticmethod
    def parse_verdict(response: str) -> bool:
        """Return True if the response contains APPROVE."""
        return "APPROVE" in response.upper()
