"""Message formatting and delivery (Telegram, console)."""
from __future__ import annotations

import html
import json
import urllib.request
from collections import Counter
from zoneinfo import ZoneInfo

from .event import ICONS, Event


def format_event(ev: Event, tz: ZoneInfo, note: str = "") -> str:
    when = ev.time.astimezone(tz).strftime("%H:%M")
    head = f"{ICONS[ev.severity]} <b>{html.escape(ev.source)}</b>"
    if ev.host:
        head += f" · {html.escape(ev.host)}"
    lines = [head, html.escape(ev.title)]
    if ev.message:
        lines.append(f"<i>{html.escape(ev.message[:600])}</i>")
    lines.append(f"{when}" + (f" · {html.escape(note)}" if note else ""))
    return "\n".join(lines)


def format_digest(events: list[Event], tz: ZoneInfo) -> str:
    if not events:
        return "☀️ <b>Daily digest</b>\nNothing happened. Quiet night in the lab."
    by_sev = Counter(e.severity for e in events)
    summary = " · ".join(f"{ICONS[s]} {by_sev[s]}" for s in ("critical", "warning", "info", "ok") if by_sev[s])
    lines = [f"☀️ <b>Daily digest</b> ({len(events)} events)", summary, ""]
    for e in sorted(events, key=lambda x: (-x.rank(), x.time))[:20]:
        lines.append(f"{ICONS[e.severity]} {e.time.astimezone(tz).strftime('%H:%M')} {html.escape(e.source)}: {html.escape(e.title)}")
    if len(events) > 20:
        lines.append(f"… and {len(events) - 20} more")
    return "\n".join(lines)


class ConsoleOutput:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> None:
        self.sent.append(text)
        print(text, "\n", flush=True)


class TelegramOutput:
    """Sends via the Telegram Bot API. Token and chat id come from the local config only."""

    def __init__(self, token: str, chat_id: str, timeout: int = 10) -> None:
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, text: str) -> None:
        body = json.dumps({"chat_id": self.chat_id, "text": text, "parse_mode": "HTML",
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 - fixed https URL
            if r.status != 200:
                raise RuntimeError(f"Telegram returned HTTP {r.status}")
