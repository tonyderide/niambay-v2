"""Tests for SelfCoder config, allowlists, and state persistence."""

import os
import re
import tempfile

from daemon.selfcoder.coder import Coder
from daemon.selfcoder.config import SelfCoderConfig
from daemon.selfcoder.planner import Planner
from daemon.selfcoder.publisher import Publisher
from daemon.selfcoder.reviewer import Reviewer
from daemon.selfcoder.scanner import Scanner
from daemon.selfcoder.state import SelfCoderState
from daemon.selfcoder.validator import Validator


def test_config_defaults():
    cfg = SelfCoderConfig()
    assert cfg.max_lines_per_cycle == 30
    assert cfg.max_files_per_cycle == 3
    assert cfg.cooldown_minutes == 30
    assert cfg.max_attempts_per_task == 2
    assert cfg.mode == "suggest"
    assert cfg.planner_model == "DeepSeek-R1-0528"
    assert cfg.coder_model == "DeepSeek-V3.2"
    assert cfg.reviewer_model == "mistral-small-latest"
    assert cfg.email_from == "niam-bay@hotmail.com"
    assert cfg.smtp_server == "smtp-mail.outlook.com"
    assert cfg.smtp_port == 587
    assert len(cfg.allowed_patterns) == 4
    assert len(cfg.forbidden_patterns) == 7
    assert len(cfg.forbidden_code_patterns) == 7


def test_config_is_path_allowed():
    cfg = SelfCoderConfig()
    assert cfg.is_path_allowed("daemon/selfcoder/config.py") is True
    assert cfg.is_path_allowed("daemon/brain/think.py") is True
    assert cfg.is_path_allowed("frontend/index.html") is True
    assert cfg.is_path_allowed("tests/test_foo.py") is True
    assert cfg.is_path_allowed("README.md") is True
    # Not in any allowed pattern
    assert cfg.is_path_allowed("random/stuff.txt") is False


def test_config_is_path_forbidden():
    cfg = SelfCoderConfig()
    # Forbidden patterns override allowed
    assert cfg.is_path_allowed("daemon/GridTradingService.py") is False
    assert cfg.is_path_allowed("daemon/ScalpingBotService.py") is False
    assert cfg.is_path_allowed("daemon/kraken/api.py") is False
    assert cfg.is_path_allowed("daemon/.env") is False
    assert cfg.is_path_allowed("config.json") is False
    assert cfg.is_path_allowed("daemon/secrets.py") is False
    assert cfg.is_path_allowed("daemon/api_key.py") is False


# --- Validator tests ---


def test_validator_ast_valid():
    v = Validator()
    assert v.check_syntax("x = 1\nprint(x)") is True
    assert v.check_syntax("def foo():\n    return 42") is True
    assert v.check_syntax("") is True  # empty code is valid


def test_validator_ast_invalid():
    v = Validator()
    assert v.check_syntax("def foo(") is False
    assert v.check_syntax("if True\n  pass") is False
    assert v.check_syntax("x = (") is False


def test_validator_forbidden_patterns():
    v = Validator()
    assert v.check_forbidden("x = 1 + 2") is True
    assert v.check_forbidden("import json") is True
    # Each forbidden pattern should be caught
    assert v.check_forbidden("os.system('rm -rf /')") is False
    assert v.check_forbidden("eval('code')") is False
    assert v.check_forbidden("exec('code')") is False
    assert v.check_forbidden("__import__('os')") is False
    assert v.check_forbidden("shutil.rmtree('/tmp')") is False
    assert v.check_forbidden("os.remove('file')") is False
    assert v.check_forbidden("subprocess.run(['ls'])") is False


def test_validator_diff_size():
    v = Validator()
    # Within limits (30 lines, 3 files)
    assert v.check_diff_size(10, 2) is True
    assert v.check_diff_size(30, 3) is True  # exact boundary
    # Over limits
    assert v.check_diff_size(31, 1) is False
    assert v.check_diff_size(10, 4) is False
    assert v.check_diff_size(100, 10) is False


def test_validator_paths():
    v = Validator()
    assert v.check_paths(["daemon/selfcoder/foo.py", "tests/test_bar.py"]) is True
    assert v.check_paths(["daemon/kraken/api.py"]) is False
    assert v.check_paths(["daemon/brain/think.py", "config.json"]) is False


# --- SelfCoderState tests ---


def test_state_creation():
    state = SelfCoderState()
    assert state.tasks_completed == []
    assert state.tasks_failed == {}
    assert state.tasks_skipped == []
    assert state.total_lines_written == 0
    assert state.total_cycles == 0
    assert state.last_run == ""
    assert state.max_attempts == 2

    state3 = SelfCoderState(max_attempts=3)
    assert state3.max_attempts == 3


def test_state_record_success():
    state = SelfCoderState()
    state.record_success("add-logging", "feat/logging", 15)
    assert "add-logging" in state.tasks_completed
    assert state.total_lines_written == 15
    assert state.total_cycles == 1
    assert state.last_run != ""

    state.record_success("fix-typo", "fix/typo", 3)
    assert len(state.tasks_completed) == 2
    assert state.total_lines_written == 18
    assert state.total_cycles == 2


def test_state_record_failure():
    state = SelfCoderState(max_attempts=2)
    state.record_failure("bad-task", "SyntaxError")
    assert state.tasks_failed["bad-task"] == 1
    assert "bad-task" not in state.tasks_skipped

    state.record_failure("bad-task", "SyntaxError again")
    assert state.tasks_failed["bad-task"] == 2
    assert "bad-task" in state.tasks_skipped


def test_state_should_skip():
    state = SelfCoderState(max_attempts=2)
    assert state.should_skip("unknown-task") is False

    state.tasks_failed["flaky"] = 1
    assert state.should_skip("flaky") is False

    state.tasks_failed["flaky"] = 2
    assert state.should_skip("flaky") is True


def test_state_save_load():
    state = SelfCoderState(max_attempts=3)
    state.record_success("task-a", "feat/a", 10)
    state.record_failure("task-b", "error")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        state.save(tmp_path)
        loaded = SelfCoderState.load(tmp_path)
        assert loaded.tasks_completed == ["task-a"]
        assert loaded.tasks_failed == {"task-b": 1}
        assert loaded.total_lines_written == 10
        assert loaded.total_cycles == 1
        assert loaded.max_attempts == 3
        assert loaded.last_run != ""
    finally:
        os.unlink(tmp_path)


# --- Scanner tests ---


def test_scanner_manual_tasks(tmp_path):
    """Scanner reads tasks.md and returns one task per line."""
    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text("# Backlog\n- Fix login bug\n- Add logging\n\n", encoding="utf-8")
    scanner = Scanner(str(tmp_path))
    tasks = scanner.find_manual_tasks()
    assert len(tasks) == 2
    assert tasks[0]["source"] == "manual"
    assert tasks[0]["description"] == "Fix login bug"
    assert tasks[0]["priority"] == 1
    assert tasks[1]["description"] == "Add logging"


def test_scanner_find_todos(tmp_path):
    """Scanner finds TODO/FIXME comments in allowed Python files."""
    pkg = tmp_path / "daemon" / "selfcoder"
    pkg.mkdir(parents=True)
    py_file = pkg / "example.py"
    py_file.write_text("x = 1\n# TODO: refactor this\n# FIXME: memory leak\n", encoding="utf-8")
    scanner = Scanner(str(tmp_path))
    todos = scanner.find_todos()
    assert len(todos) == 2
    assert todos[0]["source"] == "todo"
    assert "refactor" in todos[0]["description"]
    assert todos[0]["line"] == 2
    assert todos[1]["line"] == 3


def test_scanner_get_all_tasks_priority(tmp_path):
    """get_all_tasks returns tasks sorted by priority (manual first)."""
    # Create a manual task
    tasks_file = tmp_path / "tasks.md"
    tasks_file.write_text("- Deploy v2\n", encoding="utf-8")
    # Create a TODO
    pkg = tmp_path / "daemon" / "mod"
    pkg.mkdir(parents=True)
    (pkg / "a.py").write_text("# TODO: cleanup\n", encoding="utf-8")
    config = SelfCoderConfig(
        project_root=str(tmp_path),
        allowed_patterns=["daemon/**/*.py", "*.md"],
    )
    scanner = Scanner(str(tmp_path), config=config)
    all_tasks = scanner.get_all_tasks()
    assert len(all_tasks) >= 2
    # Manual (priority 1) should come before todo (priority 3)
    sources = [t["source"] for t in all_tasks]
    assert sources.index("manual") < sources.index("todo")


# --- Reviewer tests ---


class _FakeProvider:
    """Minimal LLMProvider stub for testing."""

    def __init__(self, reply="APPROVE\nLooks good."):
        self.reply = reply

    def chat(self, messages, **kwargs):
        from daemon.llm.base import LLMResponse
        return LLMResponse(content=self.reply, model="fake", tokens_used=0, latency_ms=0)

    def is_available(self):
        return True


def test_reviewer_creation():
    provider = _FakeProvider()
    reviewer = Reviewer(provider, model="mistral-small-latest")
    assert reviewer.provider is provider
    assert reviewer.model == "mistral-small-latest"


def test_reviewer_parse_verdict():
    assert Reviewer.parse_verdict("APPROVE\nAll good.") is True
    assert Reviewer.parse_verdict("REJECT\nFound issues.") is False
    assert Reviewer.parse_verdict("approve this code") is True
    assert Reviewer.parse_verdict("I would reject this.") is False  # no APPROVE keyword
    assert Reviewer.parse_verdict("No issues found.") is False  # no APPROVE keyword


# --- Publisher tests ---


def test_publisher_branch_name():
    pub = Publisher()
    name = pub.make_branch_name("Fix login bug")
    assert name.startswith("auto/")
    # Should contain a date-like pattern YYYY-MM-DD
    assert re.search(r"auto/\d{4}-\d{2}-\d{2}-fix-login-bug", name)


# --- Mailer tests ---

from daemon.selfcoder.mailer import Mailer


def test_mailer_creation():
    m = Mailer()
    assert m.email == "niam-bay@hotmail.com"
    assert m.smtp_server == "smtp-mail.outlook.com"
    assert m.smtp_port == 587

    m2 = Mailer(email="test@test.com", smtp_server="smtp.test.com", smtp_port=465)
    assert m2.email == "test@test.com"
    assert m2.smtp_server == "smtp.test.com"
    assert m2.smtp_port == 465


def test_mailer_format_report():
    m = Mailer()
    report = m.format_report(
        completed=[{"name": "add-logging", "branch": "feat/logging", "lines": 15, "tests": "2/2"}],
        failed=[{"name": "bad-task", "error": "SyntaxError", "attempts": 2}],
        suggestions=["Refactor daemon/brain"],
    )
    assert "COMPLÉTÉES:" in report
    assert "add-logging" in report
    assert "feat/logging" in report
    assert "+15 lignes" in report
    assert "ABANDONNÉES:" in report
    assert "bad-task" in report
    assert "SyntaxError" in report
    assert "SUGGESTIONS:" in report
    assert "Refactor daemon/brain" in report
    assert "Niam-Bay" in report

    # Empty report
    empty = m.format_report()
    assert "Rapport Niam-Bay Auto" in empty
    assert "COMPLÉTÉES:" not in empty


# --- Planner tests ---


def test_planner_creation():
    planner = Planner()
    assert planner.config.planner_model == "DeepSeek-R1-0528"
    assert planner.provider is not None
    assert planner.provider.model == "DeepSeek-R1-0528"


# --- Coder tests ---


def test_coder_creation():
    coder = Coder()
    assert coder.config.coder_model == "DeepSeek-V3.2"
    assert coder.provider is not None
    assert coder.provider.model == "DeepSeek-V3.2"
    assert coder.validator is not None


def test_coder_parse_response():
    """extract_code pulls code from ```python blocks in LLM responses."""
    response = (
        "Here is the updated file:\n\n"
        "```python\n"
        "def hello():\n"
        "    return 'world'\n"
        "```\n\n"
        "I changed the return value."
    )
    code = Coder.extract_code(response)
    assert "def hello():" in code
    assert "return 'world'" in code
    # Should not include the fence markers
    assert "```" not in code

    # No code block -> ValueError
    try:
        Coder.extract_code("No code here, just text.")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No ```python code block" in str(e)
