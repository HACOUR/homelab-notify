"""Proxmox VE notification webhook (PVE 8.2+).

Recommended body template for the Proxmox webhook target (see README):
{"title": "{{ escape title }}", "message": "{{ escape message }}",
 "severity": "{{ severity }}", "timestamp": {{ timestamp }}, "fields": {{ json fields }}}
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..event import Event

# Proxmox severities: info, notice, warning, error, unknown
_MAP = {"info": "info", "notice": "info", "warning": "warning", "error": "critical", "unknown": "warning"}


def parse(data: dict) -> Event:
    fields = data.get("fields") or {}
    sev = _MAP.get(str(data.get("severity", "info")).lower(), "info")
    title = str(data.get("title", ""))
    # Successful backups arrive as "info" - show them as ok
    if sev == "info" and fields.get("type") == "vzdump" and "success" in title.lower():
        sev = "ok"
    ts = data.get("timestamp")
    when = datetime.fromtimestamp(int(ts), timezone.utc) if str(ts or "").isdigit() else datetime.now(timezone.utc)
    return Event(source="proxmox", severity=sev, title=title, message=str(data.get("message", "")),
                 host=str(fields.get("hostname", "")), time=when)
