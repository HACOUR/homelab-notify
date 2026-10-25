import json
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, time
from http.server import ThreadingHTTPServer
from zoneinfo import ZoneInfo

from homelab_notify.config import Config
from homelab_notify.event import Event
from homelab_notify.output import ConsoleOutput, format_digest
from homelab_notify.router import Router, Rules
from homelab_notify.server import App, make_handler

TZ = ZoneInfo("Europe/Vienna")


def at(h, m=0):
    return datetime(2026, 10, 25, h, m, tzinfo=TZ)


class RouterTests(unittest.TestCase):
    def test_dedupe_and_repeat_counter(self):
        r = Router(Rules(dedupe_minutes=15))
        ev = Event("proxmox", "critical", "backup failed", host="n1")
        self.assertEqual(r.decide(ev, at(12))[0], "send")
        self.assertEqual(r.decide(ev, at(12, 5))[0], "drop")
        self.assertEqual(r.decide(ev, at(12, 20)), ("send", "+1 repeats"))

    def test_quiet_hours_over_midnight(self):
        r = Router(Rules(quiet_start=time(22), quiet_end=time(7)))
        warn = Event("synology", "warning", "SMART")
        crit = Event("proxmox", "critical", "down")
        self.assertEqual(r.decide(warn, at(23))[0], "digest")
        self.assertEqual(r.decide(crit, at(23))[0], "send")
        self.assertEqual(r.decide(Event("x", "warning", "other"), at(8))[0], "send")

    def test_min_severity(self):
        r = Router(Rules(min_severity="warning"))
        self.assertEqual(r.decide(Event("x", "ok", "fine"), at(12))[0], "digest")

    def test_digest_collects_everything(self):
        r = Router(Rules())
        r.decide(Event("a", "ok", "one"), at(1)); r.decide(Event("b", "critical", "two"), at(2))
        text = format_digest(r.take_digest(), TZ)
        self.assertIn("2 events", text)
        self.assertEqual(r.take_digest(), [])

    def test_html_is_escaped(self):
        from homelab_notify.output import format_event
        self.assertIn("&lt;script&gt;", format_event(Event("x", "info", "<script>"), TZ))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = ConsoleOutput()
        cfg = Config(token="t" * 20, rules=Rules(dedupe_minutes=0))
        cls.app = App(cfg, output=cls.out)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.app))
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def post(self, path, body, token="t" * 20, raw=False):
        data = body if raw else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data=data, headers={"X-Notify-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_health(self):
        with urllib.request.urlopen(self.url + "/health", timeout=5) as r:
            self.assertTrue(json.loads(r.read())["ok"])

    def test_rejects_bad_token(self):
        self.assertEqual(self.post("/hook/generic", {"title": "x"}, token="wrong")[0], 401)

    def test_unknown_source(self):
        self.assertEqual(self.post("/hook/nope", {"title": "x"})[0], 404)

    def test_end_to_end_proxmox(self):
        n = len(self.out.sent)
        code, body = self.post("/hook/proxmox", {"title": "backup failed", "severity": "error", "fields": {"hostname": "n1"}})
        self.assertEqual((code, body["action"]), (200, "send"))
        self.assertIn("🔴", self.out.sent[n])

    def test_plain_text_body_for_synology(self):
        code, body = self.post("/hook/synology", b"Volume 1 degraded", raw=True)
        self.assertEqual(code, 200)

    def test_too_large(self):
        self.assertEqual(self.post("/hook/generic", b"x" * 70000, raw=True)[0], 413)


if __name__ == "__main__":
    unittest.main()
