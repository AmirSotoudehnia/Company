# Agent Company

Agent Company is a controlled agentic software-delivery platform. A GitHub issue can be turned into a bounded AI patch, tested inside a hardened sandbox, pushed to a task branch, and opened as a draft pull request for human review.

## Implemented platform

### Autonomous delivery pipeline

```text
GitHub Issue / Tenant API
        |
        v
Durable Job Queue
        |
        v
Coding / Patch Agent
        |
        v
Disposable Git Workspace
        |
        v
Hardened Docker Sandbox
        |
   tests + fix loop
        |
        v
Task Branch -> Draft PR
        |
        v
Human Review / Merge
```

### Multi-tenant control plane

The platform now includes tenant isolation, one-time tenant API keys, GitHub App installation mapping, per-tenant repositories, durable jobs with leases/retries, audit logs, repository execution policies, GitHub webhook verification/deduplication, and a standalone worker process.

A repository belongs to exactly one tenant + GitHub installation mapping. Every queue and audit query is tenant-scoped. Installation tokens are short-lived and generated from the GitHub App private key; they are not stored in the database.

## Security boundaries

- No autonomous direct push to `main`.
- Draft PR only after configured tests pass.
- Human review remains required for merge/production.
- Docker sandbox defaults to no network, dropped Linux capabilities, `no-new-privileges`, read-only container root, PID/CPU/memory limits, and no GitHub/LLM secrets.
- `.env`, `.git`, path traversal and out-of-repository model writes are blocked.
- Autonomous retries and patch size/file count are bounded.
- GitHub webhooks require HMAC SHA-256 verification and delivery IDs are deduplicated.
- Tenant API keys are SHA-256 hashed at rest.

For higher-assurance third-party execution, the Docker backend should eventually be replaced or supplemented by an isolated VM/microVM or Kubernetes sandbox pool. The worker should not share privileged host credentials with code under test.

## Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Build the sandbox image:

```bash
docker build -f sandbox/Dockerfile -t agent-company-sandbox:py312 .
```

Run tests:

```bash
python -m pytest -q
```

## GitHub App configuration

Configure a GitHub App with repository permissions appropriate for Issues, Contents and Pull Requests. Store its private key only on the control/worker host.

```text
GITHUB_APP_ID=...
GITHUB_APP_PRIVATE_KEY_PATH=/run/secrets/github-app.pem
GITHUB_WEBHOOK_SECRET=...
```

`GITHUB_APP_INSTALLATION_ID` is only a legacy/single-repository fallback. Multi-tenant jobs use the installation ID stored with each tenant repository and request a short-lived token for that installation.

## Bootstrap a tenant

Set a strong `BOOTSTRAP_TOKEN`, then:

```bash
curl -X POST http://127.0.0.1:8000/tenants/bootstrap \
  -H 'Content-Type: application/json' \
  -H 'X-Bootstrap-Token: YOUR_BOOTSTRAP_TOKEN' \
  -d '{"name":"Example Customer","slug":"example"}'
```

The response contains a tenant API key exactly once. Use it as `X-Tenant-Key`.

Register the customer's GitHub App installation:

```bash
curl -X POST http://127.0.0.1:8000/tenant/installations \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Key: TENANT_KEY' \
  -d '{"installation_id":123456,"account_login":"customer-org","account_type":"Organization"}'
```

Register a repository and its execution policy:

```bash
curl -X POST http://127.0.0.1:8000/tenant/repositories \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Key: TENANT_KEY' \
  -d '{"installation_id":123456,"owner":"customer-org","name":"service","default_branch":"main","auto_code_enabled":true,"max_attempts":3,"test_command":"python -m pytest -q","required_label":"agent:run"}'
```

## Job queue

Queue manually:

```bash
curl -X POST http://127.0.0.1:8000/tenant/repositories/1/jobs/code \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Key: TENANT_KEY' \
  -d '{"issue_number":42}'
```

Or label a GitHub issue with the repository policy label (default `agent:run`). The signed `issues` webhook enqueues the job once.

Run a worker:

```bash
python -m app.worker
```

Workers claim jobs with leases. A crashed worker's lease expires and another worker can retry it. Failed jobs use bounded retries; successful jobs store their result and PR URL.

## Tenant APIs

- `GET /tenant` — current tenant
- `POST /tenant/installations` — register GitHub App installation
- `POST /tenant/repositories` — register/update repository policy
- `GET /tenant/repositories` — list isolated repositories
- `POST /tenant/repositories/{id}/jobs/code` — queue an issue
- `GET /tenant/jobs` — job state/history
- `GET /tenant/audit` — immutable-style audit trail
- `POST /webhooks/github` — signed GitHub webhook ingress

Legacy single-repository `/github/code` remains available for local development.

## What remains external to the codebase

Before public commercial launch, infrastructure/account work still has to be done outside GitHub code: create the actual GitHub App in GitHub settings, configure its callback/webhook URL and permissions, provision HTTPS hosting/database/backups, configure the model provider and secrets, and establish billing/legal/monitoring. Those require real service accounts, domains and credentials and cannot be safely fabricated by the repository itself.

## AI company loop

`python -m app.company_worker` runs the bounded recurring company loop. Each cycle asks CompanyBrain for the next action, stores it in the durable company action queue, and executes only locally safe actions.

Opportunity discovery reads an operator-controlled JSON feed from `OPPORTUNITY_FEED_FILE`. Copy `docs/opportunities_feed.example.json` to `data/opportunities_feed.json` and populate it through an authorized public feed or connector. The importer accepts only HTTP(S) source URLs and deduplicates source records.

Qualified sales opportunities create proposal records and outbound lead interactions in `draft` status. Actions involving customer contact, commercial terms, incident resolution, invoices, merge, or production remain in `waiting_human` until an operator approves and configures the relevant connector.

Operator endpoints:

- `POST /company/tick` — decide and enqueue only.
- `POST /company/run-once` — decide, enqueue, and execute one safe action.
- `GET /company` — company snapshot, queue, CRM summary, and pipeline.
- `GET /opportunities/{id}/interactions` — inspect draft lead communication.

On Windows, `scripts/install_windows_startup.ps1` installs separate API, coding-worker, and company-loop tasks. Do not place credentials in the opportunity feed or commit `.env.local`.

## Real opportunity and communication connectors

Set `JOBTECH_ENABLED=true` to use Arbetsförmedlingen's official public JobTech JobSearch endpoint. `JOBTECH_QUERY` controls the search phrase and `JOBTECH_LIMIT` is capped by the connector. Results enter the same scoring, deduplication, proposal-draft, and human-approval pipeline as manual opportunities.

Other supported ingress paths are the existing manual `POST /opportunities` endpoint and authorized GitHub issue/webhook integration. No authenticated page scraping is performed.

`POST /opportunities/{id}/interactions` records Gmail, contact-form, manual, or draft channel events. Outbound records are always forced to `draft`; inbound records become `received`. A future authenticated Gmail adapter may create or synchronize drafts, but it must never bypass owner approval.

## Real opportunity and communication connectors

Set `JOBTECH_ENABLED=true` to use Arbetsförmedlingen's official public JobTech JobSearch endpoint. `JOBTECH_QUERY` controls the search phrase and `JOBTECH_LIMIT` is capped by the connector. Results enter the same scoring, deduplication, proposal-draft, and human-approval pipeline as manual opportunities.

Other supported ingress paths are the existing manual `POST /opportunities` endpoint and authorized GitHub issue/webhook integration. No authenticated page scraping is performed.

`POST /opportunities/{id}/interactions` records Gmail, contact-form, manual, or draft channel events. Outbound records are always forced to `draft`; inbound records become `received`. A future authenticated Gmail adapter may create or synchronize drafts, but it must never bypass owner approval.
