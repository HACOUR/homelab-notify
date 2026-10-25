"""Send the example payloads to a running homelab-notify instance.

Usage: python3 scripts/simulate.py --url http://127.0.0.1:8790 --token <token>
"""
import argparse
import json
import pathlib
import urllib.request

EXAMPLES = {
    "proxmox": ["proxmox-backup-failed.json", "proxmox-backup-ok.json"],
    "uptimekuma": ["uptimekuma-down.json", "uptimekuma-up.json"],
    "synology": ["synology-smart.json"],
    "generic": ["generic-cron.json"],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8790")
    ap.add_argument("--token", required=True)
    args = ap.parse_args()
    base = pathlib.Path(__file__).resolve().parent.parent / "examples"
    for source, files in EXAMPLES.items():
        for name in files:
            body = (base / name).read_bytes()
            req = urllib.request.Request(f"{args.url}/hook/{source}", data=body,
                                         headers={"Content-Type": "application/json", "X-Notify-Token": args.token})
            with urllib.request.urlopen(req, timeout=10) as r:
                print(f"{source:<11} {name:<28} -> {json.loads(r.read())}")


if __name__ == "__main__":
    main()
