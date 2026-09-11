# Agent Company

An agentic software-delivery platform that turns a project brief or GitHub issue into a controlled engineering workflow.

## Current stage

The repository now contains two layers:

1. **Workflow MVP** — Project Manager → Developer → QA/Bug Fix → Delivery → human approval.
2. **GitHub/Coding foundation** — disposable git workspaces, branch creation, real test execution, commit/push support, draft pull-request creation, and GitHub Actions CI.

The code-generation model is deliberately separated from the execution worker. The next stage is to add a model-backed patch generator that proposes file changes while the worker remains the only component allowed to execute tests and git commands.

## Architecture

```text
Project brief / GitHub issue
          |
          v
     Orchestrator
          |
     Project Manager
          |
     Coding Agent
          |
  Disposable workspace
    |      |      |
  branch  tests  git diff
    |      |      |
    +---- QA gate -+
          |
      Draft PR
          |
   Human approval
          |
        Merge
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

## Safety boundaries

- No direct push to `main` from the coding workflow.
- Changes go to a task branch and a draft pull request.
- Tests must pass before a PR is opened.
- Production delivery remains human-approved.
- Code execution should move into an isolated container/VM before third-party repositories are supported.
- Credentials must stay in environment/secret storage and never enter prompts or logs.

## Next milestone

**Model-backed Patch Agent**

It will:

1. Read an issue and selected repository files.
2. Produce a constrained file-change plan.
3. Apply changes only inside the disposable workspace.
4. Run tests and inspect failures.
5. Retry within a strict limit.
6. Push a branch and open a draft PR when checks pass.
