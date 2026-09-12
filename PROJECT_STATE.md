# My Company - Project State

## Goal
Build a commercializable autonomous software-delivery company centered on GitHub: Issue -> planning/coding -> isolated tests -> bug-fix loop -> acceptance/review -> draft PR -> human approval -> merge/release. Human approval remains mandatory for merge and production. Opportunity/Sales agents come later.

## Hard local constraints
- All project work/data/workspaces/models belong under I:\Company.
- Keep at least 10 GB free on C: at all times; check before/after storage-heavy work.
- Prefer zero-cost local execution. Current local model: qwen2.5-coder:1.5b via Ollama.
- Ollama model storage is effectively on I:\Company\ollama-models via a junction from the default C path.
- Never commit .env.local, secrets, DBs, workspaces, model blobs, private keys, or PATs.

## Completed foundation
- FastAPI + SQLite multi-tenant platform, tenant API keys, GitHub installations/repos, durable jobs, audit logs, webhook dedup/policy, worker.
- GitHub App auth and issue/webhook workflow.
- RepositoryWorkspace clone/branch/commit/push with Windows cleanup robustness.
- Docker sandbox: no network, bounded CPU/RAM/PIDs, non-root, no secrets/socket; Windows bind-mount fix completed.
- Provider-neutral LLM client and bounded PatchAgent.
- PatchAgent supports exact find/replace, new-file content, and deterministic anchor insert_before/insert_after.
- Context selection includes endpoint entrypoint plus relevant tests.
- PatchPlanError participates in bounded retries with corrective feedback.
- Deterministic AcceptanceReviewer blocks missing requested routes/version constant before push/PR.
- Current local test suite: 26 passing.

## GitHub state
- Repo: AmirSotoudehnia/Company, default main.
- PR #1 foundation merged; PR #2 production deployment profile merged.
- Issue #3: Add /version endpoint.
- Draft PR #4 / branch agent/issue-3-version-endpoint is semantically wrong: it only changed /health from app.version to app.__version__. DO NOT MERGE.
- Later autonomous retries are fail-safe and have not pushed another bad PR.

## Current bottleneck
The orchestration/safety path works, but qwen2.5-coder:1.5b is unreliable at patch planning: exact find mismatches and sometimes malformed JSON. Latest v4 run exhausted 5 attempts with invalid JSON; nothing was pushed. Anchor-based insertion support is implemented and tested, but the small model did not reliably choose/use it.

## Next engineering priorities
1. Reduce dependence on model-generated patch mechanics: model should describe intent/target, deterministic code should locate anchors/apply edits where feasible.
2. Add robust JSON extraction/repair for small-model responses without accepting unsafe ambiguous patches.
3. Add deterministic acceptance-specific tests/guards for Issue #3, including GET /version and a single APP_VERSION source.
4. Re-run Issue #3 only after those improvements; inspect diff before considering success.
5. Keep PR #4 draft/unmerged or replace/close it after a correct branch exists.
6. Later: Ollama native /api/chat adapter for real num_ctx/keep_alive control; safe .env.local loading; deployment doc path fix; Git credential handling without token in clone URL.

## Known security/product backlog
Token-in-clone-URL when explicit token is used; SQLite is single-node; numeric GitHub repo IDs/visibility verification missing; tenant key rotation/revocation, billing, dashboard, monitoring missing; sandbox currently Python-only; stronger isolation needed for hostile multi-tenant code.

## 2026-09-12 latest progress
- Added safe balanced JSON-object extraction for noisy small-model responses; it strips surrounding prose but does not guess/repair truncated JSON.
- Added tests for noisy valid JSON and truncated invalid JSON. Full suite is now 28 passing.
- Re-ran Issue #3 as v5. JSON robustness improved, but qwen2.5-coder:1.5b still chose an invalid exact find against app/main.py on all bounded attempts. Fail-safe blocked commit/push/PR.
- Next step: implement a higher-level intent edit schema/deterministic locator so the model does not need to emit exact source snippets for common operations such as adding FastAPI routes/constants/tests.

## 2026-09-12 deterministic editor milestone
- Added DeterministicEditor for narrow auditable task patterns before LLM patch fallback.
- Issue #3 /version can now be implemented without model-generated find/replace mechanics.
- Deterministic implementation creates APP_VERSION, wires FastAPI and /health to it, adds GET /version, and creates an endpoint test when tests are required.
- Sandbox image updated with PyJWT[crypto] because importing app.main in endpoint tests requires GitHub App JWT dependency.
- Local platform suite: 32 passing. A clean main clone with the deterministic Issue #3 edit passed 14 tests in the Docker sandbox.
- Correct Issue #3 branch: agent/issue-3-version-endpoint-v8, commit addbddd66f1779ab8a6e03dc6806e261f5e24d8f.
- Draft PR #5 created for human review. Diff inspected: only app/main.py and tests/test_version_endpoint.py; 19 additions, 2 deletions. Do not auto-merge.
- Earlier v6/v7 branches are superseded; PR #4 remains known-bad and must not be merged.
- Next: verify GitHub CI for PR #5, then human-review/merge decision; afterwards commit the local platform improvements separately.
