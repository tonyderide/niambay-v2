import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

@dataclass
class Config:
    ws_port: int = 8765
    ws_host: str = "127.0.0.1"
    collect_interval: float = 2.0
    brain_path: str = str(Path.home() / ".niambay" / "brain.json")
    habits_path: str = str(Path.home() / ".niambay" / "habits.json")
    profile_path: str = str(Path.home() / ".niambay" / "profile.json")
    llm_provider: str = "ollama"
    llm_model: str = "niambay2"
    llm_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    max_memory_mb: int = 50
    max_brain_nodes: int = 10000
    observe_windows: bool = True
    observe_processes: bool = True
    observe_git: bool = True
    observe_clipboard: bool = False
    observe_browser: bool = False
    paused: bool = False
    # Voice settings
    whisper_model: str = "base"
    voice_language: str = "fr"
    tts_voice: str = "default"
    tts_speed: float = 1.0
    # MCP connectors
    mcp_gmail_enabled: bool = False
    mcp_calendar_enabled: bool = False
    mcp_custom_commands: str = "[]"
    # Appearance
    hologram_color: str = "#4fc3f7"
    animation_speed: float = 1.0
    # Privacy
    do_not_observe: bool = False

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'Config':
        with open(path) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
