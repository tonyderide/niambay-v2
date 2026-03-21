import subprocess
from .base import Collector, CollectorEvent


class GitCollector(Collector):
    name = "git"

    def __init__(self, watch_paths: list[str] = None):
        self.watch_paths = watch_paths or []

    def _run_git(self, repo_path: str, args: list[str]) -> str:
        """Run a git command in the given repo and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def _collect_repo(self, repo_path: str) -> list[CollectorEvent]:
        events = []

        branch = self._run_git(repo_path, ["branch", "--show-current"])
        if not branch:
            return events  # not a valid git repo or detached HEAD

        # modified / untracked files
        porcelain = self._run_git(repo_path, ["status", "--porcelain"])
        modified_files = len([l for l in porcelain.splitlines() if l.strip()]) if porcelain else 0

        # last commit
        last_commit = self._run_git(repo_path, ["log", "--oneline", "-1"])

        # unpushed commits
        unpushed_raw = self._run_git(repo_path, ["log", "@{u}..HEAD", "--oneline"])
        unpushed_count = len(unpushed_raw.splitlines()) if unpushed_raw else 0

        events.append(CollectorEvent(
            source="git",
            event_type="repo_status",
            data={
                "repo": repo_path,
                "branch": branch,
                "modified_files": modified_files,
                "last_commit": last_commit,
                "unpushed_commits": unpushed_count,
            },
        ))

        if unpushed_count > 3:
            events.append(CollectorEvent(
                source="git",
                event_type="unpushed_alert",
                data={
                    "repo": repo_path,
                    "branch": branch,
                    "unpushed_commits": unpushed_count,
                },
            ))

        return events

    def collect(self) -> list[CollectorEvent]:
        events = []
        for path in self.watch_paths:
            events.extend(self._collect_repo(path))
        return events
