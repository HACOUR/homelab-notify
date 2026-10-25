"""Configuration from a TOML file (Python 3.11+ tomllib)."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from .router import Rules


def _t(value: str | None) -> time | None:
    if not value:
        return None
    h, m = value.split(":")
    return time(int(h), int(m))


@dataclass
class Config:
    listen: str = "127.0.0.1"
    port: int = 8790
    token: str = ""
    timezone: str = "Europe/Vienna"
    digest_time: time | None = time(7, 30)
    telegram_token: str = ""
    telegram_chat_id: str = ""
    dry_run: bool = True
    rules: Rules = None  # type: ignore[assignment]


def load(path: str | Path) -> Config:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    srv, tg, rl = data.get("server", {}), data.get("telegram", {}), data.get("rules", {})
    token = str(srv.get("token", ""))
    if len(token) < 16 or token.startswith("<"):
        raise ValueError("server.token must be set to a random string of at least 16 characters")
    cfg = Config(
        listen=srv.get("listen", "127.0.0.1"), port=int(srv.get("port", 8790)), token=token,
        timezone=srv.get("timezone", "Europe/Vienna"), digest_time=_t(srv.get("digest_time", "07:30")),
        telegram_token=str(tg.get("bot_token", "")), telegram_chat_id=str(tg.get("chat_id", "")),
        dry_run=bool(data.get("dry_run", True)),
        rules=Rules(dedupe_minutes=int(rl.get("dedupe_minutes", 15)), quiet_start=_t(rl.get("quiet_start")),
                    quiet_end=_t(rl.get("quiet_end")), quiet_min_severity=rl.get("quiet_min_severity", "critical"),
                    min_severity=rl.get("min_severity", "ok")),
    )
    if not cfg.dry_run and (not cfg.telegram_token or cfg.telegram_token.startswith("<") or not cfg.telegram_chat_id):
        raise ValueError("telegram.bot_token and telegram.chat_id are required when dry_run = false")
    return cfg
