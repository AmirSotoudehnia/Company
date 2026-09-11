# Production deployment (single-node MVP)

This deployment profile targets a dedicated Ubuntu 24.04 server. The API and worker run as host systemd services so the worker can use Docker to create isolated sandbox containers without mounting the Docker socket into an application container.

## Architecture

```text
Internet
  |
 HTTPS
  v
 Caddy
  |
  v
 FastAPI (systemd, localhost:8000)
  |
  +---- SQLite data volume /var/lib/agent-company
  |
  +---- Worker (systemd)
             |
             v
          Docker CLI
             |
             v
      isolated sandbox containers
```

## Requirements

- Ubuntu 24.04 LTS
- 2 vCPU / 4 GB RAM minimum for small workloads
- DNS A/AAAA record pointing to the server
- GitHub App credentials
- model provider credentials

## Install

```bash
sudo bash deploy/install_ubuntu.sh
```

Then copy the environment template:

```bash
sudo cp deploy/production.env.example /etc/agent-company/agent-company.env
sudo nano /etc/agent-company/agent-company.env
```

Install the GitHub App private key as `/etc/agent-company/github-app.pem` with mode `0600` and ownership `agentcompany:agentcompany`.

Copy systemd units:

```bash
sudo cp deploy/systemd/agent-company-api.service /etc/systemd/system/
sudo cp deploy/systemd/agent-company-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now agent-company-api agent-company-worker
```

Build the sandbox image once after each sandbox Dockerfile change:

```bash
cd /opt/agent-company
sudo -u agentcompany docker build -f sandbox/Dockerfile -t agent-company-sandbox:py312 .
```

For HTTPS, copy `deploy/Caddyfile.example` to `/etc/caddy/Caddyfile`, replace the hostname, and reload Caddy.

## Backups

`deploy/backup.sh` uses SQLite's online backup command when available and creates timestamped database copies. Run it from cron/systemd timer and copy backups to a different machine/object store.

## Health checks

- `GET /health` for liveness.
- `systemctl status agent-company-api`
- `systemctl status agent-company-worker`
- `journalctl -u agent-company-api -f`
- `journalctl -u agent-company-worker -f`

## Important production notes

This is a single-node MVP profile. For higher availability, migrate the control-plane database to PostgreSQL, use a distributed queue, and move code execution to dedicated runner VMs/microVMs instead of sharing the main host's Docker daemon.