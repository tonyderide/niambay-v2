"""SelfCoder validator — multi-stage security checks."""

import ast
import subprocess

from daemon.selfcoder.config import SelfCoderConfig


class Validator:
    def __init__(self, config=None):
        self.config = config or SelfCoderConfig()

    def check_syntax(self, code: str) -> bool:
        """AST parse — is the Python code valid?"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def check_forbidden(self, code: str) -> bool:
        """No dangerous patterns in code?"""
        for pattern in self.config.forbidden_code_patterns:
            if pattern in code:
                return False
        return True

    def check_diff_size(self, lines_changed: int, files_changed: int) -> bool:
        """Within limits?"""
        return (lines_changed <= self.config.max_lines_per_cycle and
                files_changed <= self.config.max_files_per_cycle)

    def check_paths(self, file_paths: list) -> bool:
        """All files in allowlist?"""
        return all(self.config.is_path_allowed(p) for p in file_paths)

    def run_tests(self, project_root: str = None) -> tuple[bool, str]:
        """Run pytest, return (passed, output)."""
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=project_root or self.config.project_root,
            capture_output=True, text=True, timeout=120
        )
        passed = result.returncode == 0
        return passed, result.stdout + result.stderr

    def validate_all(self, code: str, lines: int, files: int, paths: list) -> tuple[bool, list]:
        """Run all checks. Returns (ok, list_of_errors)."""
        errors = []
        if not self.check_syntax(code):
            errors.append("SYNTAX: code is not valid Python")
        if not self.check_forbidden(code):
            errors.append("FORBIDDEN: dangerous pattern detected")
        if not self.check_diff_size(lines, files):
            errors.append(f"SIZE: {lines} lines / {files} files exceeds limits")
        if not self.check_paths(paths):
            bad = [p for p in paths if not self.config.is_path_allowed(p)]
            errors.append(f"PATHS: forbidden files: {bad}")
        return len(errors) == 0, errors
