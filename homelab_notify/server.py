"""HTTP server: POST /hook/<source>  (header X-Notify-Token or ?token=...)."""
from __future__ import annotations

import argparse
import hmac
import json
import logging
import threading
import time as _time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from . import __version__
from .config import Config, load
from .output import ConsoleOutput, TelegramOutput, format_digest, format_event
from .router import Router
from .sources import PARSERS

log = logging.getLogger("homelab-notify")
MAX_BODY = 64 * 1024


class App:
    def __init__(self, cfg: Config, output=None) -> None:
        self.cfg = cfg
        self.tz = ZoneInfo(cfg.timezone)
        self.router = Router(cfg.rules)
        self.output = output or (ConsoleOutput() if cfg.dry_run else TelegramOutput(cfg.telegram_token, cfg.telegram_chat_id))
        self.lock = threading.Lock()

    def handle(self, source: str, data: dict, now: datetime | None = None) -> str:
        parser = PARSERS.get(source)
        if not parser:
            raise KeyError(source)
        ev = parser(data)
        now = now or datetime.now(self.tz)
        with self.lock:
            action, note = self.router.decide(ev, now)
        if action == "send":
            self.output.send(format_event(ev, self.tz, note))
        log.info("%s %s %s: %s (%s)", action, ev.source, ev.severity, ev.title, note)
        return action

    def send_digest(self) -> None:
        with self.lock:
            events = self.router.take_digest()
        self.output.send(format_digest(events, self.tz))


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"homelab-notify/{__version__}"

        def log_message(self, fmt, *args):  # quieter default logging
            log.debug("%s %s", self.address_string(), fmt % args)

        def _reply(self, code: int, obj: dict) -> None:
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if urlparse(self.path).path == "/health":
                return self._reply(200, {"ok": True, "version": __version__})
            self._reply(404, {"error": "not found"})

        def do_POST(self):
            url = urlparse(self.path)
            parts = url.path.strip("/").split("/")
            if len(parts) != 2 or parts[0] != "hook":
                return self._reply(404, {"error": "use POST /hook/<source>"})
            given = self.headers.get("X-Notify-Token") or parse_qs(url.query).get("token", [""])[0]
            if not hmac.compare_digest(given, app.cfg.token):
                return self._reply(401, {"error": "invalid token"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._reply(413, {"error": "payload too large"})
            raw = self.rfile.read(length) if length else b""
            try:
                data = json.loads(raw or b"{}")
                if not isinstance(data, dict):
                    raise ValueError("JSON object expected")
            except ValueError:
                # Synology/ntfy-style plain text bodies are accepted as {"text": ...}
                data = {"text": raw.decode("utf-8", "replace")}
            try:
                action = app.handle(parts[1], data)
            except KeyError:
                return self._reply(404, {"error": f"unknown source '{parts[1]}'", "sources": sorted(PARSERS)})
            except Exception as exc:  # noqa: BLE001 - never crash the server on a bad payload
                log.exception("failed to handle %s", parts[1])
                return self._reply(500, {"error": str(exc)})
            self._reply(200, {"ok": True, "action": action})

    return Handler


def digest_loop(app: App, stop: threading.Event) -> None:
    sent_on = None
    while not stop.is_set():
        now = datetime.now(app.tz)
        dt = app.cfg.digest_time
        if dt and now.time().replace(second=0, microsecond=0) == dt and sent_on != now.date():
            app.send_digest()
            sent_on = now.date()
        stop.wait(20)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="homelab-notify")
    ap.add_argument("-c", "--config", default="config.toml")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load(args.config)
    app = App(cfg)
    stop = threading.Event()
    threading.Thread(target=digest_loop, args=(app, stop), daemon=True).start()
    srv = ThreadingHTTPServer((cfg.listen, cfg.port), make_handler(app))
    log.info("listening on %s:%s (dry_run=%s)", cfg.listen, cfg.port, cfg.dry_run)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        srv.server_close()
        _time.sleep(0.1)


if __name__ == "__main__":
    main()
