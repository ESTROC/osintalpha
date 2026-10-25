# OSINT Alpha V7 — Bounded investigation engine and captured source quotations

## Delivered

### Resumable guided investigation
- Start a saved investigation objective with a 1–8 query budget.
- Every step is persisted separately with provider, query, rationale, result counts, errors and timestamps. Research jobs can be resumed after refreshing the browser.
- With explicit case remote-AI consent and configured GROQ_API_KEY, a Groq model *proposes* the next permitted public query based on saved lead summaries and previous query outcomes.
- Only listed providers run. Model suggestions must contain the original case subject or a known public handle, are bounded in length and must not duplicate prior searches. It cannot execute arbitrary URLs or commands.
- When model access is unavailable or its output invalid, the engine uses an explicitly labelled rules-based source plan.
- Optional Brave web discovery requires BRAVE_SEARCH_API_KEY and separately confirmed external-search consent. Without the credential, the UI states it is unavailable.
- Each browser-initiated run can be resumed from its persisted checkpoint. No claim of always-on background execution or general autonomous browser access.

### Verbatim captured-source passages
- Store text quotations matched exactly to captured source text with a SHA-256 integrity check.
- Link each quotation to one capture, original public-source record, authoring analyst and interpretation.
- Flag quotations whose captured source has later changed. Excerpts appear in analyst findings and exported reports.
- Passing exact match proves the text is in the capture. It does **not** independently verify a person's identity, the page's authenticity or the factual truth of the text.

### Release quality
- Tests for agent authorization, remote consent, step resumption, duplicate-execution prevention, model query constraints, case isolation and quotation integrity.
- Existing 95-issue matrix remains open until each acceptance test is satisfied. New features should not be represented as certified enterprise intelligence.

## Excluded and unresolved scope

Provider-recall benchmarks, identity matching calibrated to ground truth, full claim entailment, unattended durable background workers, unrestricted web retrieval, SSO/MFA, enterprise multi-tenant isolation, external security review, verified backups and human analyst evaluations are not implemented or independently demonstrated.

Render Free PostgreSQL remains a time-limited database. Do not treat it as production-grade retention for client investigations.

## Environment

Configured only on the backend: OSINTALPHA_ADMIN_PASSWORD, DATABASE_URL for PostgreSQL, optional GROQ_API_KEY and BRAVE_SEARCH_API_KEY. Keys must never be exposed to the frontend, repository, logs or reports.
