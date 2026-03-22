"""Gmail connector — MCP-ready stub."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Email:
    sender: str
    subject: str
    snippet: str = ""
    date: str = ""
    unread: bool = True
    id: str = ""
    labels: List[str] = field(default_factory=list)


class GmailConnector:
    name = "gmail"

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path
        self._service = None

    @property
    def enabled(self) -> bool:
        return self._service is not None

    def fetch_unread(self) -> List[Email]:
        """Fetch unread emails. Stub — returns empty list until wired to API."""
        return []

    def format_summary(self, emails: List[Email]) -> str:
        """Format a human-readable summary of emails."""
        if not emails:
            return "No unread emails."
        lines = [f"{len(emails)} unread email(s):"]
        for e in emails:
            flag = "[unread] " if e.unread else ""
            lines.append(f"  - {flag}{e.sender}: {e.subject}")
        return "\n".join(lines)
