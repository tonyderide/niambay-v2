"""SelfCoder Publisher — git operations for auto-generated branches."""

import re
import subprocess
from datetime import date
from typing import List


def _run(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=True, **kwargs)


class Publisher:
    """Handles git branch creation, commit, push, and cleanup."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def make_branch_name(self, description: str) -> str:
        """Generate branch name: auto/YYYY-MM-DD-slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", description.lower()).strip("-")
        return f"auto/{date.today().isoformat()}-{slug}"

    def create_branch(self, name: str) -> None:
        """Create and checkout a new branch."""
        _run(["git", "checkout", "-b", name], cwd=self.repo_path)

    def commit(self, message: str, files: List[str]) -> None:
        """Stage files and commit."""
        _run(["git", "add"] + files, cwd=self.repo_path)
        _run(["git", "commit", "-m", message], cwd=self.repo_path)

    def push(self, branch: str) -> None:
        """Push branch to origin."""
        _run(["git", "push", "origin", branch], cwd=self.repo_path)

    def back_to_master(self) -> None:
        """Switch back to master."""
        _run(["git", "checkout", "master"], cwd=self.repo_path)

    def cleanup(self, branch: str) -> None:
        """Delete a local branch."""
        _run(["git", "branch", "-D", branch], cwd=self.repo_path)
