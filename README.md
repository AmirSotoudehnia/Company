# Agent Company

An agentic software-delivery platform that turns a project brief or GitHub issue into a controlled engineering workflow.

## Current stage

The repository now contains five layers:

1. **Workflow MVP** — Project Manager → Developer → QA/Bug Fix → Delivery → human approval.
2. **GitHub/Coding foundation** — disposable git workspaces, branch creation, commit/push support, draft pull-request creation, and GitHub Actions CI.
3. **Model-backed Patch Agent** — bounded repository context, constrained file edits, test-feedback retries, branch push, and draft PR creation.
4. **Docker Sandbox** — test execution in an isolated container with no network by default, dropped Linux capabilities, PID/CPU/memory limits, read-only container filesystem, and no forwarded GitHub/LLM secrets.
5. **GitHub App authentication** — short-lived per-installation tokens are preferred over long-lived personal repository tokens.

The model is deliberately separated from the execution worker. The model can only propose complete text-file replacements inside a bounded repository context; the worker remains the only component allowed to execute tests and git commands.

## Architecture

```text
GitHub issue
    |
    v
Issue reader
    |
    v
Patch Agent (LLM)
    |
constrained edit plan
    |
    v
Disposable git workspace
    |
 apply edits
    |
    v
Docker Sandbox
(no network / no secrets / resource limits)
    |
 run tests
    |\
    | fail -> feed test output back to Patch Agent -> retry (bounded)
    |
   pass
    |
 commit + push task branch
    |
 draft pull request
    |
 human review / approval
```

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` or API docs at `http://127.0.0.1:8000/docs`.

## Build the sandbox image

Docker must be installed on the worker host.

```bash
docker build -f docker/sandbox.Dockerfile -t agent-company-sandbox:py312 .
```

The autonomous coding path defaults to `EXECUTION_MODE=docker`. Local shell execution is blocked unless `ALLOW_LOCAL_EXECUTION=true` is explicitly set for trusted development.

## Run tests

```bash
python -m pytest -q
```

## GitHub authentication

### Recommended: GitHub App

Create a GitHub App with repository-scoped permissions and install it only on repositories the platform should manage. Configure:

```text
GITHUB_APP_ID=
GITHUB_APP_INSTALLATION_ID=
GITHUB_APP_PRIVATE_KEY_PATH=/secure/path/private-key.pem
GITHUB_OWNER=AmirSotoudehnia
GITHUB_REPO=Company
```

An inline `GITHUB_APP_PRIVATE_KEY` is also supported, but a mounted secret/file is preferable in production.

The worker creates a short-lived installation token at runtime and keeps it in memory only. It is used for Git clone/push and REST API operations, then refreshed before expiry.

### Development fallback

```text
GITHUB_TOKEN=
```

A long-lived token should only be used for trusted local development. GitHub App authentication takes precedence when both are configured.

## Sandbox configuration

```text
EXECUTION_MODE=docker
ALLOW_LOCAL_EXECUTION=false
SANDBOX_IMAGE=agent-company-sandbox:py312
SANDBOX_MEMORY=1g
SANDBOX_CPUS=1.0
SANDBOX_PIDS=256
SANDBOX_NETWORK=none
SANDBOX_USER=1000:1000
```

Security controls applied to every sandbox run:

- `--network none` by default.
- `--cap-drop ALL`.
- `no-new-privileges`.
- CPU, memory and PID limits.
- read-only container root filesystem.
- temporary writable `/tmp` and home mounts only.
- repository workspace mounted separately.
- GitHub token, GitHub App private key and LLM API key are not passed into the container.
- Docker socket is never mounted into the sandbox.

## LLM configuration

The current client accepts an OpenAI-compatible chat-completions endpoint without coupling the worker to one vendor.

```text
LLM_MODE=remote
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=...
LLM_MODEL=...
```

Keep `LLM_MODE=mock` when you do not want autonomous model calls.

## Trigger autonomous issue coding

With the API running, sandbox image built, and GitHub/LLM variables configured:

```bash
curl -X POST http://127.0.0.1:8000/github/code \
  -H "Content-Type: application/json" \
  -d '{"issue_number": 12, "max_attempts": 3}'
```

The worker reads the issue, creates an `agent/issue-12` branch, asks the Patch Agent for a constrained edit plan, applies it in a disposable workspace, runs tests inside the Docker sandbox, retries with test feedback when needed, then pushes and opens a draft pull request only after tests pass.

## Safety boundaries

- No direct push to `main` from the autonomous coding workflow.
- Changes go to a task branch and a draft pull request.
- Tests must pass before a PR is opened.
- Model edits are limited by file count and total byte size.
- `.env`, `.git`, parent-directory escapes and out-of-repository writes are blocked.
- Production delivery remains human-approved.
- Untrusted repository code executes in the Docker sandbox, not the control-plane process.
- Credentials stay outside repository workspaces and sandbox environments.

## Next milestone

**Multi-tenant GitHub App installations + job queue**

The next commercial milestone is to stop relying on one globally configured repository. Each customer/organization will have its own GitHub App installation id, allowed repositories, execution policy, queue, audit trail, and usage budget. The control plane will select the correct installation credential per job and dispatch isolated workers without exposing one customer's credentials or workspace to another.
