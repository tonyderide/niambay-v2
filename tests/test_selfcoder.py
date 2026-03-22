"""Tests for SelfCoder config and allowlists."""

from daemon.selfcoder.config import SelfCoderConfig


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
