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
