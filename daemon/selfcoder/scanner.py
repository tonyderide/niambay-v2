"""SelfCoder scanner — finds tasks from multiple sources."""

import re
import subprocess
from pathlib import Path
from typing import List

from daemon.selfcoder.config import SelfCoderConfig


class Scanner:
    """Scans the project for actionable tasks from multiple sources."""

    def __init__(self, project_root: str, config: SelfCoderConfig | None = None):
        self.root = Path(project_root)
        self.config = config or SelfCoderConfig(project_root=project_root)

    # ------------------------------------------------------------------
    # Source 1: manual tasks from tasks.md
    # ------------------------------------------------------------------

    def find_manual_tasks(self) -> list[dict]:
        """Read tasks.md if it exists. Each non-empty line = a task."""
        tasks_file = self.root / "tasks.md"
        if not tasks_file.is_file():
            return []

        results: list[dict] = []
        for i, raw in enumerate(tasks_file.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Strip leading "- " or "* " bullet markers
            desc = re.sub(r"^[-*]\s+", "", line)
            results.append({
                "source": "manual",
                "description": desc,
                "file": "tasks.md",
                "line": i,
                "priority": 1,
            })
        return results

    # ------------------------------------------------------------------
    # Source 2: failing tests
    # ------------------------------------------------------------------

    def find_failing_tests(self) -> list[dict]:
        """Run pytest --tb=line, parse failures."""
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", "--tb=line", "-q"],
                capture_output=True,
                text=True,
                cwd=str(self.root),
                timeout=120,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

        results: list[dict] = []
        # pytest --tb=line outputs lines like:
        #   FAILED tests/test_foo.py::test_bar - AssertionError: ...
        # or one-line tracebacks like:
        #   path/file.py:42: AssertionError
        fail_re = re.compile(r"^FAILED\s+(\S+?)::(\S+)")
        tb_re = re.compile(r"^(.+\.py):(\d+):\s+(.+)")

        for raw in proc.stdout.splitlines():
            line = raw.strip()
            m = fail_re.match(line)
            if m:
                fpath, test_name = m.group(1), m.group(2)
                results.append({
                    "source": "test",
                    "description": f"Failing test: {test_name}",
                    "file": fpath,
                    "line": 0,
                    "priority": 2,
                })
                continue
            m = tb_re.match(line)
            if m:
                fpath, lineno, msg = m.group(1), int(m.group(2)), m.group(3)
                # Avoid duplicates if we already captured from FAILED line
                if not any(t["file"] == fpath and t["source"] == "test" for t in results):
                    results.append({
                        "source": "test",
                        "description": f"Test failure: {msg}",
                        "file": fpath,
                        "line": lineno,
                        "priority": 2,
                    })
        return results

    # ------------------------------------------------------------------
    # Source 3: TODO / FIXME comments
    # ------------------------------------------------------------------

    def find_todos(self) -> list[dict]:
        """Find TODO|FIXME comments in allowed Python files."""
        todo_re = re.compile(r"#\s*(TODO|FIXME)\b[:\s]*(.*)", re.IGNORECASE)
        results: list[dict] = []

        for py_file in self.root.rglob("*.py"):
            rel = str(py_file.relative_to(self.root)).replace("\\", "/")
            if not self.config.is_path_allowed(rel):
                continue
            try:
                lines = py_file.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for i, line in enumerate(lines, 1):
                m = todo_re.search(line)
                if m:
                    tag, msg = m.group(1), m.group(2).strip()
                    results.append({
                        "source": "todo",
                        "description": f"{tag}: {msg}" if msg else tag,
                        "file": rel,
                        "line": i,
                        "priority": 3,
                    })
        return results

    # ------------------------------------------------------------------
    # Source 4: code smells (long functions / large files)
    # ------------------------------------------------------------------

    def find_smells(self) -> list[dict]:
        """Find functions > 50 lines and files > 300 lines."""
        func_re = re.compile(r"^(\s*)def\s+(\w+)\s*\(")
        results: list[dict] = []

        for py_file in self.root.rglob("*.py"):
            rel = str(py_file.relative_to(self.root)).replace("\\", "/")
            if not self.config.is_path_allowed(rel):
                continue
            try:
                lines = py_file.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue

            # Large file smell
            if len(lines) > 300:
                results.append({
                    "source": "smell",
                    "description": f"Large file ({len(lines)} lines)",
                    "file": rel,
                    "line": 1,
                    "priority": 4,
                })

            # Long function smell
            func_starts: list[tuple[str, int, int]] = []  # (name, start, indent)
            for i, line in enumerate(lines, 1):
                m = func_re.match(line)
                if m:
                    indent = len(m.group(1))
                    func_starts.append((m.group(2), i, indent))

            for idx, (name, start, indent) in enumerate(func_starts):
                # Function body ends at next def with same or less indent, or EOF
                if idx + 1 < len(func_starts):
                    end = func_starts[idx + 1][1] - 1
                else:
                    end = len(lines)
                length = end - start + 1
                if length > 50:
                    results.append({
                        "source": "smell",
                        "description": f"Long function '{name}' ({length} lines)",
                        "file": rel,
                        "line": start,
                        "priority": 4,
                    })

        return results

    # ------------------------------------------------------------------
    # Aggregator
    # ------------------------------------------------------------------

    def get_all_tasks(self) -> list[dict]:
        """Merge all sources, sorted by priority (lower = higher priority)."""
        all_tasks: List[dict] = []
        all_tasks.extend(self.find_manual_tasks())
        all_tasks.extend(self.find_failing_tests())
        all_tasks.extend(self.find_todos())
        all_tasks.extend(self.find_smells())
        all_tasks.sort(key=lambda t: t["priority"])
        return all_tasks
