"""Uptime Kuma webhook (JSON mode): {"heartbeat": {...}, "monitor": {...}, "msg": "..."}"""
from __future__ import annotations

from ..event import Event

# heartbeat.status: 0 = down, 1 = up, 2 = pending, 3 = maintenance
_STATUS = {0: ("critical", "down"), 1: ("ok", "up again"), 2: ("warning", "pending"), 3: ("info", "maintenance")}


def parse(data: dict) -> Event:
    hb = data.get("heartbeat") or {}
    mon = data.get("monitor") or {}
    name = str(mon.get("name") or "monitor")
    if not hb:  # test notification from the Uptime Kuma UI
        return Event(source="uptimekuma", severity="info", title=f"{name}: test", message=str(data.get("msg", "")))
    sev, word = _STATUS.get(hb.get("status"), ("info", "status changed"))
    detail = str(hb.get("msg") or data.get("msg") or "")
    target = str(mon.get("url") or mon.get("hostname") or "")
    return Event(source="uptimekuma", severity=sev, title=f"{name} {word}", message=detail, host=target)
