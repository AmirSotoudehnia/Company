#!/usr/bin/env bash
set -euo pipefail

APP_USER=agentcompany
APP_DIR=/opt/agent-company
ENV_DIR=/etc/agent-company
DATA_DIR=/var/lib/agent-company

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install_ubuntu.sh" >&2
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl git python3 python3-venv python3-pip docker.io caddy sqlite3
systemctl enable --now docker caddy

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
fi
usermod -aG docker "$APP_USER"

mkdir -p "$APP_DIR" "$ENV_DIR" "$DATA_DIR" /var/backups/agent-company
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$DATA_DIR" /var/backups/agent-company
chmod 0750 "$ENV_DIR" "$DATA_DIR" /var/backups/agent-company

if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone https://github.com/AmirSotoudehnia/Company.git "$APP_DIR"
else
  git -C "$APP_DIR" fetch --all --prune
  git -C "$APP_DIR" reset --hard origin/main
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
sudo -u "$APP_USER" docker build -f "$APP_DIR/docker/sandbox.Dockerfile" -t agent-company-sandbox:py312 "$APP_DIR"

cp "$APP_DIR/deploy/systemd/agent-company-api.service" /etc/systemd/system/
cp "$APP_DIR/deploy/systemd/agent-company-worker.service" /etc/systemd/system/
systemctl daemon-reload

echo "Base install completed. Configure $ENV_DIR/agent-company.env and GitHub App key, then enable services."