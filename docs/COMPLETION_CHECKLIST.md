# My Company - Completion Checklist

Last updated: 2026-09-14
Canonical repository: AmirSotoudehnia/Company
Canonical local root: I:\Company

## Completed and merged

- Multi-tenant FastAPI control plane, durable jobs, audit logs, GitHub App workflow.
- PM, Architect, Developer, QA, Bug Fix, Code Review, Security, Delivery agents.
- Hardened Docker execution, bounded patch retries, deterministic acceptance gates.
- Opportunity scoring, sales proposals, approval gates, CRM, customer intake and change control.
- Customer communication drafts, monitoring, incidents, invoices, live control panel.
- CompanyBrain, recurring durable company actions, local feed ingestion and deduplication.
- Official public Arbetsförmedlingen JobTech discovery.
- Manual, GitHub, Gmail/contact-form interaction ingress with outbound forced to draft.

## Local Operational MVP completed (2026-09-14)

- Owner profile fixed to local Windows, ChatGPT Gmail, and unregistered legal status.
- Explicit Gmail-draft outbox approval; approval never marks a message sent.
- Operator dashboard exposes outbox and invoice drafts.
- Tenant API-key issue/list/revoke lifecycle; final active key cannot be revoked.
- Immutable draft-invoice approval/rejection lifecycle (not an official tax invoice).
- Build profile registry for Python, Node/TypeScript, Flutter, .NET and Kotlin.
- Baseline browser security headers and end-to-end safety regression tests.
- Revenue-focused control panel for service leads, freelance projects, buyer/seller matching and general commercial research.
- Strict candidate gating: unverified results and snippet-derived contacts cannot enter sales.
- JobTech retained only as a legacy optional connector, not the primary company search.

## Deferred expansion work (not required for the selected local-only profile)

- Add direct provider adapters beyond the selected ChatGPT Gmail handoff.
- Build and validate dedicated Docker images for non-Python stack profiles.
- Generate official invoice PDFs after legal registration and tax details exist.
- Add PostgreSQL, migrations, restore drills and production health checks if deployment becomes public.
- Add live lead-to-payment testing after real customer and payment-provider data exist.
- Add distributed rate limiting and centralized logs if the service leaves the local computer.

## External blockers

- Gmail decision resolved: ChatGPT Gmail with owner-approved drafts only.
- Legal decision resolved for MVP: unregistered; official invoices remain unavailable.
- Deployment decision resolved for MVP: zero-cost, local Windows only.
- Accounting/payment provider selection and credentials.
- Real customer/recipient data for an end-to-end live test.

## Non-negotiable safety gates

- No automatic commercial commitment.
- No automatic outbound message or invoice send.
- No automatic merge or production deployment.
- No secrets, databases, workspaces, model blobs, private keys or PATs in Git.
- Keep at least 10 GB free on C:.
- Perform all local project work under I:\Company.

This file and PROJECT_STATE.md are the continuation sources. Read both before starting new work.
