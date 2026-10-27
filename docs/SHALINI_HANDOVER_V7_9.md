# OSINT Alpha V7.9 — Shalini analyst handover and remaining-work register
Date: 2026-10-27

## Single-search experience delivered in this release

1. A prominent, natural-language search box accepts an analyst question such as "Ayush cybersecurity Indian Navy"; the investigator records a lawful purpose and authorization, with separate consent for remote Groq.
2. The backend creates a persisted case and chooses a tentative subject and bounded public-source plan. With explicit opt-in and a working Groq key, Groq assists with **source routing**. Without it, an explainable deterministic fallback remains functional. It never confirms identity.
3. Up to three permitted structured APIs are automatically collected into versioned source records where relevant. A question about an ordinary tradesperson does not automatically trigger academic search.
4. When Brave and Groq are configured and consented, the case is answered through question-specific Brave LLM Context excerpts plus newly saved case evidence. When Brave context errors, the UI exposes a warning and retries using saved case evidence only (not hidden fresh browsing).
5. If remote AI is not authorized or configured, a configured Brave web query can still save public candidate links; the interface explicitly labels the fallback as **source-only**, not generative AI.
6. The primary investigation tabs are Search & answer, Sources, Report, and Case overview. The former specialist tabs remain reachable through **More analyst tools**.
7. The results view exposes candidate source URLs, provider statuses, human review states, consented model output and case conversation history. The resulting profile is not automatically verified.

## Remaining work: release-blocking before a real client trial

| ID | Work | Risk/acceptance gate | Current state |
| --- | --- | --- | --- |
| P0-01 | Real Brave Search and LLM Context validation with actual configured key | Confirm successful responses, original URLs, quota behavior and accurate snippets; do not publish the key | NOT VERIFIED IN LIVE PROVIDER BENCHMARK |
| P0-02 | Real Groq model / source-router validation | Test provider JSON output, budgets, timeouts, retries, fallback with realistic prompts | NOT VERIFIED IN LIVE PROVIDER BENCHMARK |
| P0-03 | Independent identity/name-collision evaluation | Manually adjudicate a consented set of multi-name cases; measure false-positive rate, abstention and source precision | OPEN |
| P0-04 | Final-browser usability and accessibility test | Verify search, sources, review and PDF on mobile/desktop in an actual browser, beyond simulated JS smoke | OPEN |
| P0-05 | Analyst role / permissions / workspace scoping | Create separate analyst login; grant only intended cases; confirm cannot read another user's cases; test logout | EXISTING CODE; LIVE ACCEPTANCE OPEN |
| P0-06 | Database expiry, backups and restore | Free Render Postgres expiry is 2026-11-23; migrate/upgrade and prove restore before real case information | CRITICAL OPEN |
| P0-07 | Provider failure, quotas and costs | Rate limits, monthly budget caps, real-world failure and degraded-mode tests | PARTIAL |
| P0-08 | Clear personal-data handling | Explicit authorized purposes, retention/deletion, audit, nonpublic data prohibition and access-control review | PARTIAL |

## Important post-trial development work

| Area | Remaining capability |
| --- | --- |
| Relevance | Ground-truth dataset, adaptive query reformulation, local/global source discovery, query expansion, provider health and stale-data handling |
| AI behavior | Iterative source planning informed by actual returned results, guarded tool calling, explainable prioritization, abstention, source-specific factual entailment and citation accuracy scoring |
| Identity | Evidence-backed entity resolution, reliable namesake exclusion, conflict flags, longitudinal facts with timestamps; never auto-merge persons from same names |
| Sources | More relevant official public records by jurisdiction and question; consented first-party profiles and business registries, with terms and licensing checked |
| Accuracy | Evidence-level independent corroboration, quotes and original captures, trusted-versus-opinion signals, strong distinction between publisher assertions and verified facts |
| Multimedia | Original-publisher media with rights, source provenance, timestamps and verified ownership of account photos; no photo-based person identification without independent basis |
| Geo | City/public-point map with source and observation timestamp, business/organization locations; camera feeds remain separate from person search and cannot establish private-person whereabouts |
| Reports | First-class concise search results, reproducible claim-to-source citations, conflict and limitation sections, export audit and redactable sharing |
| Security | MFA/SSO, password reset/revocation, authorization tests, rate limits, malicious prompt-injection defenses, independent security and privacy review |
| Ops | Secret rotation, key usage and cost telemetry, background job queue with cancellation/retry, observability and alerts, backup policy, tested restore and cost/stability baselines |
| UI | Progressive search statuses, model/provider failure detail, mobile/browser accessibility QA, sortable sources, case persistence and full search-result navigation |
| Open-source projects | The external tools referenced in UPSTREAM_MANIFEST.md (e.g., OSIRIS, World Monitor, SpiderFoot, Sherlock, OpenAleph, OpenCTI) are not installed subsystems. Each addition requires actual integration and a license/data-rights/security review, not a link or logo. |

## Hands-on acceptance scenarios for Shalini

- Search **"Ayush cybersecurity Indian Navy"** and check whether the system asks for identity clues rather than wrongly merging unrelated public academic authors, employee profiles or code accounts. Examine each source link.
- Search a common personal name with a deliberately unrelated same-name result; expected: explicit ambiguity, no auto-confirmation.
- Search a student's public competition/event participation; expected: relevant public index results without irrelevant academic-publication assumptions.
- Search a tradesperson or service provider's public business listing; expected: service/business discovery as unverified candidate records, not a résumé.
- Search a clearly identified organization and check original legal registry or verified company page, if supported for that jurisdiction.
- Search a public IP or domain; expected: passive-only technical lookups with no scanning.
- Turn off Groq case consent; expected: no remote model source router or Groq answer, visible source-only fallback.
- Revoke/invalid Brave credentials or hit a quota; expected: visible provider error and no fabricated fresh findings.
- Try private-person live location or residential address tracking; expected rejection.
- Sign in as an analyst account; expected access to owned/explicitly shared cases only.

## Honest release statement

This release has tested **workflow logic**, not a certified general-purpose person identification or intelligence engine. Passing pytest and mock-console checks is not an independent real-world assessment. Do not report 95/95 of the historical audit; the original 95 complete item texts are not available for fresh item-by-item certification.

## Suggested Shalini trial

Use synthetic or clearly permitted public subjects. Give Shalini a distinct **analyst** account rather than sharing administrator credentials. Collect feedback using: initial question, expected answer, actual answer, original links, wrong namesakes, missing source, AI hallucination, elapsed time and severity. Any person identification or important due-diligence conclusion requires independent analyst review before dissemination.
