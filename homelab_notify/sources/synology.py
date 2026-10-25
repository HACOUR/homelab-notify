"""Synology DSM custom webhook.

DSM sends whatever body you configure. Recommended: {"text": "@@TEXT@@"}
Severity is guessed from keywords, because DSM does not send one.
"""
from __future__ import annotations

import re

from ..event import Event

_CRIT = re.compile(r"\b(fail(ed|ure)?|crash(ed)?|degraded|error|abnormal|unreachable)\b", re.I)
_WARN = re.compile(r"\b(warning|smart|almost full|low|bad sector|reconnect)\b", re.I)
_OK = re.compile(r"\b(success(fully)?|completed|restored|healthy|back online)\b", re.I)


def parse(data: dict) -> Event:
    text = str(data.get("text") or data.get("message") or "").strip()
    first, _, rest = text.partition("\n")
    sev = "critical" if _CRIT.search(text) else "warning" if _WARN.search(text) else "ok" if _OK.search(text) else "info"
    return Event(source="synology", severity=sev, title=first or "Synology notification",
                 message=rest.strip(), host=str(data.get("hostname", "")))
