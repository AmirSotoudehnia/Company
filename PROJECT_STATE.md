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
## 2026-09-12 PR #6 review milestone
- PR #5 passed GitHub CI and was squash-merged into main at 8529dd942fbca3fcfc0815c2bc8a761a12202dd9.
- Known-bad PR #4 was closed without merge.
- feature/local-ollama was rebased onto the new main and pushed as PR #6: Harden autonomous coding pipeline.
- Local post-rebase suite: 33 passing.
- GitHub CI for PR #6 passed successfully on commit 5b05f0167e497b06a758d65337965fda14035440.
- PR #6 diff reviewed at a high level: deterministic acceptance/editing, safer PatchAgent parsing, endpoint-aware context, Windows workspace/sandbox fixes, local LLM controls, PyJWT sandbox dependency, tests, and state tracking.
- No merge is allowed until human approval; next action is mark PR #6 ready for review after this state update passes CI.

## 2026-09-12 core hardening batch
- PR #6 passed CI and was squash-merged to main at be9bbabf851720677f4b2a6a95066b4751504f0f.
- AcceptanceReviewer now receives changed files, requires a changed test file when the task requires tests, and verifies /version test coverage.
- LLM retries now reset tracked/untracked workspace changes between attempts so failed patches cannot accumulate.
- Git transport no longer embeds explicit tokens in remote URLs; temporary GIT_ASKPASS credentials are used and deleted after transport.
- .env.local is loaded safely with existing environment variables taking precedence; no dotenv dependency is required.
- Native Ollama /api/chat mode added so num_ctx, num_predict, and keep_alive controls are sent to Ollama directly; live local probe succeeded with qwen2.5-coder:1.5b.
- Deployment docs/install script now use the real docker/sandbox.Dockerfile path.
- Expanded regression suite: 38 tests passing locally. C: remained above the 10 GB minimum.
- Work branch: feature/core-hardening-batch. Next gate: push, create PR, verify GitHub CI, human-approved merge only.
## 2026-09-12 PM + Architect milestone
- PR #7 passed CI and was squash-merged to main at bb90a3b15dbde3c322f26bf59f5af2e4768a3076.
- Added a structured ProjectManagerAgent plan: objective, acceptance criteria, workstreams, and risk notes.
- Added ArchitectAgent repository inspection: stack, entrypoints, test locations, constraints, and implementation order.
- Orchestrator flow is now PM -> Architect -> Developer -> QA/Bug Fix -> Delivery -> human approval.
- Added architecture task seeding and ordering/regression tests.
- Local suite: 41 tests passing; C: remains above 10 GB.
- Work branch: feature/pm-architect-agents; next gate is GitHub CI then human-approved merge.

## 2026-09-12 Security + Code Review milestone
- PR #8 passed GitHub CI and was squash-merged to main at 1452ccd5b1c9c57a17a5614d41c847581fa221e6.
- Added independent CodeReviewAgent after QA, with a fail-closed review_blocked state.
- Added SecurityAgent after code review, with a fail-closed security_blocked state.
- Release preparation now runs only after both quality and security gates pass.
- Seeded explicit code-review and security tasks in the orchestrator workflow.
- Added regression tests for pass/block behavior and gate ordering.
- Local suite: 46 tests passing; human production approval remains required.
- Work branch: feature/security-code-review-agents; next gate is GitHub CI then human-approved merge.

## 2026-09-12 Opportunity + Sales milestone
- PR #9 passed CI and was squash-merged to main at 8aaae97822346c7d74e0bac328641b13d1a51911.
- Added OpportunityAgent for capability-fit scoring, qualification, and risk flags.
- Added SalesAgent that drafts proposals but never sends or commits terms automatically.
- Added persistent opportunities and sales_approvals tables plus SalesPipeline.
- Added opportunity create/list/get and explicit proposal-approval API endpoints.
- Qualified opportunities stop at a human approval gate before any customer outreach.
- Risky/low-fit opportunities remain not_ready and create no outbound approval action.
- Local suite: 50 tests passing; C: remains above the 10 GB minimum.
- Work branch: feature/opportunity-sales-pipeline; next gate is GitHub CI then human-approved merge.
