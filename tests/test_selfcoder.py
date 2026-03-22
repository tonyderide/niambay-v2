"""Tests for SelfCoder config, allowlists, and state persistence."""

import os
import tempfile

from daemon.selfcoder.config import SelfCoderConfig
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
