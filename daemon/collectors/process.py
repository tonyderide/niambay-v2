import psutil
from .base import Collector, CollectorEvent


class ProcessCollector(Collector):
    name = "process"

    def __init__(self, cpu_threshold: float = 80.0, memory_threshold: float = 90.0):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold

    def collect(self) -> list[CollectorEvent]:
        events = []

        # System-wide stats
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Top 10 processes by RAM
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_percent"]):
            try:
                info = p.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        top_procs = sorted(procs, key=lambda x: x.get("memory_percent") or 0, reverse=True)[:10]

        events.append(CollectorEvent(
            source=self.name,
            event_type="system_stats",
            data={
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024 ** 3), 2),
                "memory_total_gb": round(memory.total / (1024 ** 3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024 ** 3), 2),
                "disk_total_gb": round(disk.total / (1024 ** 3), 2),
                "top_processes": top_procs,
            },
        ))

        # Alerts
        if cpu_percent > self.cpu_threshold:
            events.append(CollectorEvent(
                source=self.name,
                event_type="alert",
                data={"alert": "high_cpu", "value": cpu_percent, "threshold": self.cpu_threshold},
            ))

        if memory.percent > self.memory_threshold:
            events.append(CollectorEvent(
                source=self.name,
                event_type="alert",
                data={"alert": "high_memory", "value": memory.percent, "threshold": self.memory_threshold},
            ))

        if disk.percent > 90.0:
            events.append(CollectorEvent(
                source=self.name,
                event_type="alert",
                data={"alert": "high_disk", "value": disk.percent, "threshold": 90.0},
            ))

        return events
