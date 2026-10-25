"""Normalized event that every source is converted into."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Ordered from harmless to critical
SEVERITIES = ("ok", "info", "warning", "critical")
ICONS = {"ok": "🟢", "info": "🔵", "warning": "🟡", "critical": "🔴"}


@dataclass
class Event:
    source: str            # e.g. "proxmox", "uptimekuma", "synology"
    severity: str          # one of SEVERITIES
    title: str
    message: str = ""
    host: str = ""
    time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            self.severity = "info"
        self.title = (self.title or "").strip() or "(no title)"
        self.message = (self.message or "").strip()
        self.host = (self.host or "").strip()

    @property
    def key(self) -> str:
        """Identity for de-duplication: same source, host and title."""
        return f"{self.source}|{self.host}|{self.title}".lower()

    def rank(self) -> int:
        return SEVERITIES.index(self.severity)
