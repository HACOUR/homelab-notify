import tempfile
import unittest
from pathlib import Path

from homelab_notify.config import load

EXAMPLE = Path(__file__).resolve().parent.parent / "config.example.toml"


class ConfigTests(unittest.TestCase):
    def write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(text); f.close()
        return f.name

    def test_example_with_placeholder_token_is_rejected(self):
        with self.assertRaises(ValueError):
            load(EXAMPLE)

    def test_example_with_real_token_loads(self):
        text = EXAMPLE.read_text().replace("<RANDOM-STRING-MIN-16-CHARS>", "a" * 24)
        cfg = load(self.write(text))
        self.assertTrue(cfg.dry_run)
        self.assertEqual(cfg.rules.quiet_start.hour, 22)

    def test_telegram_required_when_not_dry_run(self):
        text = EXAMPLE.read_text().replace("<RANDOM-STRING-MIN-16-CHARS>", "a" * 24).replace("dry_run = true", "dry_run = false")
        with self.assertRaises(ValueError):
            load(self.write(text))


if __name__ == "__main__":
    unittest.main()
