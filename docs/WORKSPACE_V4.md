# OSINT Alpha V4 — Analyst Workbench

## Status (25 October 2026)
Working evaluation release. Not a certified, proven, comprehensive OSINT platform.

### What an analyst can do
1. Sign in with an administrator or individual analyst account. Cases are owner-scoped for analysts.
2. Select person, organization, domain or public IP and enter an authorized purpose.
3. Add known public context: city, organization, profession and handle.
4. View a bounded source-query plan. Choose quick, standard or thorough research depth.
5. Execute allowlisted collectors and inspect **actual query text, provider status, returned candidates, new records and failures**.
6. Inspect evidence, search/filter and bulk review with mandatory notes.
7. Group distinct candidate identities without automatic merging. Attach specific source records, explain relationships, and mark unresolved, potential, excluded or confirmed-by-analyst.
8. Enter concrete evidence-linked claims (support, contradict, context) and analyst assessment fields (summary, findings, uncertainty, next steps).
9. Resume saved AI conversations, optionally perform Groq browser search with explicit case consent. Model-reported URLs are unverified leads requiring human review.
10. Export HTML/PDF assessment with candidate hypotheses, claims, record provenance, sources searched and limitations.

### Research accuracy limitations
- Source adapters are **specialist APIs**, not a web index. Some profiles, portfolios or news references will be missed. APIs may rate-limit or omit records.
- Input clues affect planning of extra bounded queries, but no independent comprehensive search/index or autonomous research engine is installed.
- Triage compares source attributes, not guaranteed identities. Unknown attributes are not contradictions.
- Candidate profile grouping is human-controlled, not machine-verified. Analyst confirmation is not official identity proof.
- Groq's browser search is provider-operated; output citations and links may be missing. The application does not automatically archive external pages or verify that passages support claims.
- No authoritative identity score, threat attribution, live location tracking, private dataset access or automatic allegation generation.

### Key API endpoints
- GET /api/cases/{id}/research-plan?depth=standard
- POST /api/cases/{id}/research
- GET /api/cases/{id}/research-history
- GET/POST /api/cases/{id}/candidates
- PATCH /api/cases/{id}/candidates/{candidate_id}
- POST /api/cases/{id}/candidates/{candidate_id}/sources
- POST /api/cases/{id}/evidence/bulk-review
- GET/PUT /api/cases/{id}/assessment
- GET /api/cases/{id}/intelligence
- GET /api/cases/{id}/report-v4.html
- GET /api/cases/{id}/report-v4.pdf

### Persistence
PostgreSQL tables for users, sessions, cases, evidence, source collection, audit, public subject clues, conversations, messages, search history, claims, per-query execution, candidate profiles, candidate-to-source links and assessments.

**Render free PostgreSQL is a time-limited evaluation database.** Its free-instance expiry was previously reported as November 23, 2026 UTC. Before collecting real or valuable data: move to a persistent paid tier, configure backups and test restore. Data in previous SQLite installations was not automatically imported.

### Release tests
- Python compileall
- Pytest synthetic API and security regression tests (source APIs and model calls mocked; no assumption of real-world accuracy)
- Node static JS syntax check
- V3 and V4 simulated DOM flow smoke checks
- Live deployment readiness and HTTP health checks through Vercel/Render

### Still not solved; release cannot be called a unicorn or certified enterprise platform
- General-purpose indexed web discovery and source content archiving
- Calibrated cross-platform identity resolution against validated benchmark data
- Agentic multi-step source searching and independent citation-entailment checks
- Native case collaboration, review/approval workflow and robust tenant isolation
- SSO/MFA, password recovery, enterprise key policy and external penetration testing
- Durable paid infrastructure, backup restores, migration tools and monitoring
- Threat intelligence feed fusion, STIX/TAXII, full malware triage, AIS/ADS-B, remote sensing
- Fine-grained advanced search/query-building, large-scale pagination and continuous alerting
- Formal privacy/licensing program and audited user outcomes

## Definition of success
Run 30–50 consented or synthetic same-name research tasks and compare with Google Search and ChatGPT. Measure evidence relevance, precision, recall, unsupported claims, identity false positives, time to an acceptable assessment, source access errors and report quality. A shipping checklist is not an accuracy benchmark.
