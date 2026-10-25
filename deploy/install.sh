#!/bin/sh
# Installs homelab-notify on Debian 12 (e.g. a small LXC). Run as root from the repo folder.
set -e
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
id homelab-notify >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin homelab-notify
mkdir -p /opt/homelab-notify /etc/homelab-notify
cp -r homelab_notify /opt/homelab-notify/
if [ ! -f /etc/homelab-notify/config.toml ]; then
  cp config.example.toml /etc/homelab-notify/config.toml
  echo "Created /etc/homelab-notify/config.toml - edit it (token, telegram), then: systemctl restart homelab-notify"
fi
chown -R root:homelab-notify /etc/homelab-notify && chmod 750 /etc/homelab-notify && chmod 640 /etc/homelab-notify/config.toml
cp deploy/homelab-notify.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now homelab-notify
systemctl --no-pager status homelab-notify | head -5
