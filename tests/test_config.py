import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from daemon.config import Config

def test_default_config():
    cfg = Config()
    assert cfg.ws_port == 8765
    assert cfg.collect_interval == 2.0
    assert cfg.llm_provider == "ollama"
    assert cfg.llm_model == "niambay2"
    assert cfg.brain_path is not None
    assert cfg.max_memory_mb == 50

def test_config_from_dict():
    cfg = Config(ws_port=9000, llm_provider="anthropic")
    assert cfg.ws_port == 9000
    assert cfg.llm_provider == "anthropic"

def test_config_save_load(tmp_path):
    cfg = Config(ws_port=9999)
    path = tmp_path / "config.json"
    cfg.save(str(path))
    cfg2 = Config.load(str(path))
    assert cfg2.ws_port == 9999
