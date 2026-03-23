"""SelfCoder configuration and path allowlists."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _glob_to_regex(pattern: str) -> re.Pattern:
    """Convert a glob pattern (with ** support) to a compiled regex."""
    parts = pattern.replace("\\", "/").split("/")
    regex_parts = []
    for i, part in enumerate(parts):
        if part == "**":
            # ** matches zero or more path segments
            regex_parts.append("(?:.+/)?")
        else:
            r = ""
            for ch in part:
                if ch == "*":
                    r += "[^/]*"
                elif ch == "?":
                    r += "[^/]"
                elif ch in r"\.+^${}()|[]":
                    r += "\\" + ch
                else:
                    r += ch
            regex_parts.append(r + "/")
    full = "".join(regex_parts)
    # If pattern ends with /**, it should match everything below
    if full.endswith("(?:.+/)?"):
        full = full[:-len("(?:.+/)?")] + ".*"
    elif full.endswith("/"):
        full = full[:-1]
    return re.compile("^" + full + "$")


@dataclass
class SelfCoderConfig:
    # Cycle limits
    max_lines_per_cycle: int = 50
    max_files_per_cycle: int = 3
    cooldown_minutes: int = 30
    max_attempts_per_task: int = 2

    # Mode: "suggest" (email diff for approval) or "auto" (apply directly)
    mode: str = "suggest"

    # Paths
    project_root: str = str(Path.cwd())
    state_path: str = str(Path.home() / ".niambay" / "selfcoder_state.json")

    # LLM models
    planner_model: str = "DeepSeek-V3-0324"  # V3 not R1 — R1 adds <think> tags that break JSON parsing
    coder_model: str = "DeepSeek-V3-0324"
    reviewer_model: str = "mistral-small-latest"

    # Email
    email_from: str = "niam-bay@hotmail.com"
    email_to: str = "niam-bay@hotmail.com"
    smtp_server: str = "smtp-mail.outlook.com"
    smtp_port: int = 587

    # Allowlists
    allowed_patterns: List[str] = field(default_factory=lambda: [
        "daemon/**/*.py",
        "frontend/**/*",
        "tests/**/*.py",
        "*.md",
    ])

    forbidden_patterns: List[str] = field(default_factory=lambda: [
        "**/GridTradingService*",
        "**/ScalpingBotService*",
        "**/kraken/**",
        "**/*.env",
        "**/config.json",
        "**/secrets*",
        "**/*key*",
    ])

    forbidden_code_patterns: List[str] = field(default_factory=lambda: [
        "os.system(",
        "subprocess.run(",
        "eval(",
        "exec(",
        "__import__(",
        "shutil.rmtree(",
        "os.remove(",
    ])

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed for editing.

        A path must match at least one allowed pattern
        and must not match any forbidden pattern.
        """
        normalized = path.replace("\\", "/")

        # Check forbidden first — forbidden wins
        for pattern in self.forbidden_patterns:
            if _glob_to_regex(pattern).match(normalized):
                return False

        # Must match at least one allowed pattern
        for pattern in self.allowed_patterns:
            if _glob_to_regex(pattern).match(normalized):
                return True

        return False
