import json
import pathlib
import unittest

from homelab_notify.sources import PARSERS

EX = pathlib.Path(__file__).resolve().parent.parent / "examples"


def load(name):
    return json.loads((EX / name).read_text(encoding="utf-8"))


class SourceTests(unittest.TestCase):
    def test_proxmox_failed_backup_is_critical(self):
        ev = PARSERS["proxmox"](load("proxmox-backup-failed.json"))
        self.assertEqual(ev.severity, "critical")
        self.assertEqual(ev.host, "<NODE>")
        self.assertIn("backup failed", ev.title)

    def test_proxmox_successful_backup_is_ok(self):
        self.assertEqual(PARSERS["proxmox"](load("proxmox-backup-ok.json")).severity, "ok")

    def test_proxmox_unknown_severity(self):
        self.assertEqual(PARSERS["proxmox"]({"title": "x", "severity": "strange"}).severity, "info")

    def test_uptimekuma_down_and_up(self):
        down = PARSERS["uptimekuma"](load("uptimekuma-down.json"))
        up = PARSERS["uptimekuma"](load("uptimekuma-up.json"))
        self.assertEqual((down.severity, up.severity), ("critical", "ok"))
        self.assertEqual(down.title, "<WEBSITE> down")

    def test_uptimekuma_test_notification(self):
        ev = PARSERS["uptimekuma"]({"heartbeat": None, "monitor": None, "msg": "Test"})
        self.assertEqual(ev.severity, "info")

    def test_synology_keywords(self):
        self.assertEqual(PARSERS["synology"](load("synology-smart.json")).severity, "warning")
        self.assertEqual(PARSERS["synology"]({"text": "Backup task failed"}).severity, "critical")
        self.assertEqual(PARSERS["synology"]({"text": "Backup task completed successfully"}).severity, "ok")

    def test_generic(self):
        ev = PARSERS["generic"](load("generic-cron.json"))
        self.assertEqual((ev.source, ev.severity), ("cron", "ok"))


if __name__ == "__main__":
    unittest.main()
