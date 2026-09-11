# Agent Company

An agentic software-delivery platform that turns a project brief or GitHub issue into a controlled engineering workflow.

## Current stage

The repository now contains three layers:

1. **Workflow MVP** — Project Manager → Developer → QA/Bug Fix → Delivery → human approval.
2. **GitHub/Coding foundation** — disposable git workspaces, branch creation, real test execution, commit/push support, draft pull-request creation, and GitHub Actions CI.
3. **Model-backed Patch Agent** — bounded repository context, constrained file edits, real test execution, test-feedback retries, branch push, and draft PR creation.

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
Disposable workspace
    |
 apply edits
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

## Run tests

```bash
pytest -q
```

## GitHub configuration

Copy `.env.example` to `.env` and set a token with access only to the repository you intend the worker to modify. Do not use an account-wide token in production. The commercial version should use a GitHub App with per-installation repository permissions.

Required variables:

```text
GITHUB_TOKEN=
GITHUB_OWNER=AmirSotoudehnia
GITHUB_REPO=Company
WORKSPACE_ROOT=/tmp/agent-company-workspaces
TEST_COMMAND=pytest -q
```

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

With the API running and GitHub/LLM variables configured:

```bash
curl -X POST http://127.0.0.1:8000/github/code \
  -H "Content-Type: application/json" \
  -d '{"issue_number": 12, "max_attempts": 3}'
```

The worker reads the issue, creates an `agent/issue-12` branch, asks the Patch Agent for a constrained edit plan, applies it in a disposable workspace, runs the configured test command, retries with test feedback when needed, then pushes and opens a draft pull request only after tests pass.

## Safety boundaries

- No direct push to `main` from the autonomous coding workflow.
- Changes go to a task branch and a draft pull request.
- Tests must pass before a PR is opened.
- Model edits are limited by file count and total byte size.
- `.env`, `.git`, parent-directory escapes and out-of-repository writes are blocked.
- Production delivery remains human-approved.
- Code execution should move into an isolated container/VM before third-party repositories are supported.
- Credentials must stay in environment/secret storage and never enter prompts or logs.

## Next milestone

**Containerized execution + GitHub App authentication**

Before supporting customer repositories, the worker should execute third-party code inside an isolated container/VM and replace repository tokens with per-installation GitHub App credentials. After that we can add specialized reviewer/security agents and usage/billing controls.
