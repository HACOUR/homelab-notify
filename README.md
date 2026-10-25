# homelab-notify

![status: beta](https://img.shields.io/badge/status-beta-orange) ![python](https://img.shields.io/badge/python-3.11%2B-blue) ![deps](https://img.shields.io/badge/dependencies-none-brightgreen)

**One notification bridge for the homelab.** Proxmox, Uptime Kuma, Synology and your own
scripts send their alerts to homelab-notify - it turns them into one consistent format and
delivers them to a Telegram bot.

```
🔴 proxmox · <NODE>
vzdump backup status (<NODE>): backup failed
CT <CT-ID> (<CT-NAME>): ERROR: no space left on device
03:12

🟢 uptimekuma · https://<DOMAIN>
<WEBSITE> up again
200 - OK
03:14 · +2 repeats
```

> **⚠ Beta:** All parsers and rules are tested with simulated payloads (see `examples/`).
> Real Proxmox, Uptime Kuma, Synology and Telegram connections have **not been tested end-to-end yet**.

## Features

- **Sources:** Proxmox VE (webhook target, PVE 8.2+), Uptime Kuma (webhook), Synology DSM (custom webhook), generic JSON for scripts and cron jobs
- **One format:** severity icon, source, host, title, details, time
- **De-duplication:** the same alert within *n* minutes is sent once, repeats are counted
- **Quiet hours:** at night only critical alerts get through, the rest goes into the digest
- **Daily digest:** a morning summary of everything that happened
- **No dependencies:** Python 3.11+ standard library only - runs in the smallest LXC
- **Dry run:** prints to the console instead of Telegram - safe for testing

## Quick start

```bash
git clone https://github.com/HACOUR/homelab-notify && cd homelab-notify
cp config.example.toml config.toml        # set server.token, keep dry_run = true for now
python3 -m homelab_notify -c config.toml  # terminal 1
python3 scripts/simulate.py --token <your-token>   # terminal 2: sends the example alerts
```

## Install as a service (Debian 12 / LXC)

```bash
sudo ./deploy/install.sh                  # creates user, /opt/homelab-notify, systemd unit
sudo nano /etc/homelab-notify/config.toml # token, Telegram, dry_run = false
sudo systemctl restart homelab-notify
curl http://<HOST>:8790/health
```

## Telegram bot

1. In Telegram, talk to **@BotFather** → `/newbot` → copy the **bot token**.
2. Send any message to your new bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id`.
3. Put both into `config.toml` (never into the repo - `config.toml` is git-ignored).

## Connecting the sources

All sources call `POST http://<HOST>:8790/hook/<source>` with the header `X-Notify-Token: <token>`
(or `?token=<token>` if a source cannot set headers).

### Proxmox VE
*Datacenter → Notifications → Add → Webhook*
- Method `POST`, URL `http://<HOST>:8790/hook/proxmox`
- Header `X-Notify-Token` = `{{ secrets.token }}`, secret `token` = your token
- Header `Content-Type` = `application/json`
- Body:
```
{"title": "{{ escape title }}", "message": "{{ escape message }}", "severity": "{{ severity }}", "timestamp": {{ timestamp }}, "fields": {{ json fields }}}
```
Then add the webhook to a notification matcher.

### Uptime Kuma
*Settings → Notifications → Setup Notification → Webhook*
- URL `http://<HOST>:8790/hook/uptimekuma?token=<token>`, request body **application/json**

### Synology DSM
*Control Panel → Notification → Webhooks → Add → Custom*
- URL `http://<HOST>:8790/hook/synology?token=<token>`, method `POST`
- Body `{"text": "@@TEXT@@"}`
Synology sends no severity - it is derived from keywords (failed / warning / completed …).

### Your own scripts
```bash
curl -s -X POST http://<HOST>:8790/hook/generic -H "X-Notify-Token: <token>" \
  -d '{"source":"cron","severity":"ok","title":"Nightly rsync finished","host":"<HOST>"}'
```
Severities: `ok`, `info`, `warning`, `critical`.

## Security

- Run it **inside your LAN** (or behind a VPN). It is not meant to be exposed to the internet.
- Every request needs the token; payloads are limited to 64 KB; HTML in messages is escaped.
- Secrets (token, Telegram) live only in `config.toml` on the host.

## Test status

| Area | Unit tests | Real system |
|---|---|---|
| Proxmox parser | ✅ simulated payloads | ⏳ |
| Uptime Kuma parser | ✅ | ⏳ |
| Synology parser | ✅ | ⏳ |
| Router (dedupe, quiet hours, digest) | ✅ | — |
| HTTP server (token, limits, plain text) | ✅ | ⏳ |
| Telegram output | dry run only | ⏳ |

Run the tests: `python3 -m unittest discover -s tests -v`

## Roadmap

- More outputs: mail, Discord, ntfy
- More sources: Proxmox Backup Server, Jellyfin, AMP
- Commands from Telegram (`/status`) - step towards a homelab assistant

## License

MIT - see [LICENSE](LICENSE).
