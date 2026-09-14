# My Company - Project State

## Goal
Build an AI-operated software company: continuously discover real opportunities -> qualify -> sales/CRM -> owner approval for commitments -> customer intake -> plan/build/test/fix/review/security -> delivery -> invoice/follow-up -> repeat. GitHub/Docker/LLM are internal execution tools, not the product goal. Human approval remains mandatory for commercial commitments, merge, and production.

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

## 2026-09-12 Customer Operations milestone
- PR #10 passed CI #45 and was squash-merged to main at f6fa0228319e4ed02bc79144b65fc53339bc2c0e.
- Added Customer Intake: approved sales opportunities can become customer engagements.
- Added scope, acceptance criteria, budget, deadline, milestones, and explicit scope-commitment approval.
- Scope approval creates the executable project; unapproved scope cannot enter delivery workflow.
- Added scope-creep protection through pending Change Requests with separate approval records.
- Added CustomerCommunicationAgent and persistent draft communications; outbound sending is intentionally not automatic.
- Added Monitoring + Operations health-check records, job summary dashboard, and automatic incident creation for unhealthy checks.
- Operational monitoring records/escalates state but does not mutate/deploy production automatically.
- Local suite: 54 tests passing; C: remains above the 10 GB minimum.
- Work branch: feature/customer-ops-batch; next gate is GitHub CI then user-authorized merge.

## 2026-09-13 Customer Operations finalization
- PR #11 passed GitHub CI #47 and was merged into main.
- Merge SHA: a4133ffaee1c0d5800465c226a6e40fd9a90bc11.
- Local I:\Company was synchronized to origin/main at a4133ff.
- Post-merge local regression suite: 54 passed, 3 deprecation warnings.
- C drive free space after finalization: 14.69 GB (minimum requirement remains >=10 GB).
- Customer Intake + scope/milestones, Customer Communication, and Monitoring/Operations are now on main.
- Human approval remains required before outbound customer commitments/messages and production-sensitive actions.
- Multi-stack support remains intentionally deferred.

## 2026-09-13 Live Control Panel milestone
- Added a live web control panel at /control with automatic 2-second refresh.
- Added persistent per-agent activity: idle/running/completed/failed/paused, current project/job, detail, and timestamp.
- Orchestrated PM/Architect/Developer/QA/BugFix/Review/Security/Delivery activity is recorded live.
- Background Coding Agent activity is recorded against queue job IDs.
- Added operator Pause/Resume controls for agents and Retry/Cancel controls for queue jobs.
- Dashboard includes projects, jobs/workers, pending approvals, and open incidents.
- Human approval gates for customer commitments, merge, and production remain unchanged.
- Local regression suite: 56 passed, 3 warnings; live /control smoke test returned HTTP 200.
- Work branch: feature/live-control-panel; next gate is GitHub CI and human-approved merge.


## 2026-09-13 Business autonomy pivot
- Corrected the canonical goal: the product is an AI-operated company, not merely a GitHub coding pipeline.
- Added CompanyBrain (CEO loop) that inspects incidents, approvals, active delivery, queue, invoices and pipeline and selects the next safe company action.
- CEO decisions are persisted in company_cycles and exposed through /company and /company/tick.
- Added provider-neutral OpportunityDiscovery ingestion for real public-feed/connector opportunities with URL validation; authenticated external accounts remain connector/API based, not unauthorized scraping.
- Added CRM company pipeline/summary views.
- Added lead_interactions foundation for future inbound/outbound conversation history.
- Added CEO to live agent control roster.
- Regression suite: 62 passed, 1 third-party deprecation warning.
- Next focus: connect authorized real opportunity sources and customer communication channels, then make CompanyBrain schedule the full recurring business loop.

## 2026-09-13 Recurring company action queue milestone
- Added a durable company_actions queue for CompanyBrain decisions.
- Each /company/tick now schedules the selected safe business action and returns its queue record.
- Pending/running actions are deduplicated by action type, preventing recurring CEO ticks from flooding the queue.
- /company now exposes queued company actions alongside the business snapshot and CRM pipeline.
- No outbound message, commercial commitment, merge, deployment, or invoice send is executed automatically.
- Regression suite: 63 passed, 1 third-party deprecation warning.
- Work branch: feature/company-recurring-loop.
- Next focus: add bounded action executors, beginning with configured public opportunity feeds and draft-only customer communication; keep authenticated services connector-based and owner-approved.

## 2026-09-13 Safe company action execution milestone
- Added company_worker with a bounded recurring CEO loop and durable action claiming/completion.
- Configured local JSON opportunity feeds are ingested from inside I:\Company only.
- Opportunity source URLs are validated and duplicate source records are skipped.
- Qualified opportunities create outbound proposal interactions in draft status only.
- Human-dependent actions stop in waiting_human; no message, contract, invoice, merge, or deployment is sent automatically.
- Added /company/run-once and operator-protected lead-interaction inspection.
- Added Windows company-loop runner/startup task definitions and a safe example feed.
- Regression suite: 66 passed, 1 third-party deprecation warning.
- Work branch: feature/company-action-execution.
- External authenticated connectors still require real service selection, authorization, and credentials from the owner.

## 2026-09-14 Real source and communication ingress milestone
- Added the official public Arbetsförmedlingen/JobTech JobSearch connector with bounded queries and result conversion.
- Company discovery can combine JobTech results with the private local JSON feed.
- Manual opportunity ingestion and authorized GitHub issue/webhook paths remain available.
- Added operator-protected Gmail/contact-form/manual interaction ingestion.
- Outbound interactions are forced to draft; inbound interactions are stored as received.
- No authenticated scraping or automatic outbound sending was added.
- Regression suite: 68 passed, 1 third-party deprecation warning.
- Work branch: feature/real-opportunity-connectors.
- Remaining external step: authorize a real Gmail account/connector before draft synchronization can be activated.

## 2026-09-14 Completion checkpoint
- Added docs/COMPLETION_CHECKLIST.md as the canonical remaining-work and external-blocker checklist.
- Future work must read PROJECT_STATE.md and the completion checklist before editing.
- GitHub operations are authorized for this repository; production, outbound commercial actions and spending remain separately gated.
- Gmail is installed in ChatGPT, but the local service still needs an OAuth/provider boundary or ChatGPT-based orchestration decision.


## 2026-09-14 Local Operational MVP completion
- Owner profile persisted: local Windows only, ChatGPT Gmail, legal status unregistered.
- Added explicit outbound outbox approvals. Approval permits Gmail draft creation only; it never records a send.
- Control panel now exposes and decides project, sales, scope, Gmail-draft and invoice gates.
- Added tenant API-key issue/list/revoke lifecycle with final-key protection.
- Added immutable invoice draft decisions; official tax invoices remain disabled while unregistered.
- Added Python, Node/TypeScript, Flutter, .NET and Kotlin build-profile registry.
- Added baseline security headers and safety regression coverage.
- Local regression suite: 77 passed, 1 third-party deprecation warning.
- Health/profile smoke test passed; C: free space remained about 24.49 GB.
- Remaining items are external/public-scale expansions, not blockers for the selected local MVP.


## 2026-09-14 Panel-driven opportunity search
- Added a persistent Find Work form to /control with query and result-limit inputs.
- Save & start search immediately queries the official JobTech source and stores new opportunities.
- The saved query persists in SQLite and is reused by recurring discovery cycles.
- Added operator-protected GET /control/search and POST /control/search/start endpoints.
- Live JobTech smoke test returned a real result for "flutter developer".
- Regression suite: 79 passed, 1 third-party deprecation warning.


## 2026-09-14 Local business lead search
- Diagnosed the no-op panel: an older running API could serve the updated static page without the new search routes.
- Split panel discovery into Job advertisements and Local businesses missing a website.
- Added bounded OpenStreetMap/Nominatim connector with Växjö Persian/Latin aliases and public-service retries.
- Local-business results are verification leads only: a missing OSM website tag is not proof that no website exists.
- Live Växjö probe returned five candidate records; subsequent public-service load was handled as a visible error.
- Regression suite: 80 passed, 1 third-party deprecation warning.


## 2026-09-14 Search observability
- Added durable search_runs tracking with running/completed/failed state, counts, timestamps and errors.
- Control panel now shows search activity and up to 50 recent opportunity results.
- Each result displays name, source, qualification score, pipeline status and clickable source URL.
- Search failures remain visible instead of appearing as a no-op.
- Regression suite: 81 passed, 1 third-party deprecation warning.


## 2026-09-14 General research agent
- Added Auto and General Web modes for natural-language public-web research using Tavily.
- Research missions, stages, failures and cited findings are durable and visible in the control panel.
- Findings expose source links, snippet-derived contact hints and confidence, and require explicit promotion before becoming sales opportunities.
- Sales approval now queues bounded company research and tailored outreach preparation; outbound sending remains separately gated.
- The Tavily secret is loaded from ignored .env.local and is never returned or logged.
- Live Persian smoke search completed with five stored sources; regression suite: 84 passed, 1 warning.
- Private CRM text must not be sent to Tavily without explicit authorization.


## 2026-09-14 Revenue opportunity redesign
- Replaced the primary employment-oriented panel flow with a revenue-objective workflow.
- Natural-language objectives are classified as service leads, freelance projects, trade matching, or general commercial research.
- Trade matching searches buyer and seller roles separately and never claims profit without price, cost, logistics and compliance inputs.
- Every result is a candidate with explicit verification and risk status; snippet-derived emails and phone numbers are not exposed as verified data.
- Only fully verified candidates can enter the sales pipeline. Unverified, audit-required and due-diligence-required candidates are blocked.
- CompanyBrain now prioritizes recurring revenue opportunity discovery; JobTech remains a legacy optional connector.
- Live smoke tests covered SEO lead discovery and oil buyer/seller matching without outreach or transaction execution.
- Regression suite: 89 passed, 1 warning; control-panel JavaScript validation passed.
