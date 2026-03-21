from dataclasses import dataclass
from typing import Any
import time

@dataclass
class CollectorEvent:
    source: str
    event_type: str
    data: dict
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class Collector:
    name: str = "base"

    def collect(self) -> list[CollectorEvent]:
        raise NotImplementedError

    def cleanup(self):
        pass
