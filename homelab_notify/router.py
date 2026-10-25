"""De-duplication, quiet hours and the daily digest."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from .event import Event


@dataclass
class Rules:
    dedupe_minutes: int = 15
    quiet_start: time | None = None      # e.g. 22:00
    quiet_end: time | None = None        # e.g. 07:00
    quiet_min_severity: str = "critical"  # what still gets through at night
    min_severity: str = "ok"              # below this: digest only


@dataclass
class Router:
    rules: Rules
    _last_sent: dict = field(default_factory=dict)
    _suppressed: dict = field(default_factory=dict)
    digest: list = field(default_factory=list)

    def _in_quiet(self, local_now: datetime) -> bool:
        s, e = self.rules.quiet_start, self.rules.quiet_end
        if not s or not e:
            return False
        t = local_now.time()
        return (s <= t or t < e) if s > e else (s <= t < e)

    def decide(self, ev: Event, local_now: datetime) -> tuple[str, str]:
        """Return (action, note). action = send | digest | drop."""
        from .event import SEVERITIES
        self.digest.append(ev)
        last = self._last_sent.get(ev.key)
        if last and local_now - last < timedelta(minutes=self.rules.dedupe_minutes):
            self._suppressed[ev.key] = self._suppressed.get(ev.key, 0) + 1
            return "drop", "duplicate"
        if ev.rank() < SEVERITIES.index(self.rules.min_severity):
            return "digest", "below min severity"
        if self._in_quiet(local_now) and ev.rank() < SEVERITIES.index(self.rules.quiet_min_severity):
            return "digest", "quiet hours"
        self._last_sent[ev.key] = local_now
        repeats = self._suppressed.pop(ev.key, 0)
        return "send", (f"+{repeats} repeats" if repeats else "")

    def take_digest(self) -> list:
        items, self.digest = self.digest, []
        return items
