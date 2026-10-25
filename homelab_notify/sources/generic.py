"""Generic JSON: {"title", "message", "severity", "host"} - for scripts and cron jobs."""
from __future__ import annotations

from ..event import Event


def parse(data: dict) -> Event:
    return Event(source=str(data.get("source") or "generic"), severity=str(data.get("severity", "info")).lower(),
                 title=str(data.get("title", "")), message=str(data.get("message", "")), host=str(data.get("host", "")))
