# P0 Batch 001–010: reconciled with current P1 main

Release candidate date: 2026-10-27. Integration branch: `integration/p0-001-010-on-current-main-20261027`. Integration started from `e0da27799617a73971ef0d3de2fd0d5b9d8b872c` to **preserve newer P1 029–038 query routing and adaptive Brave features** while combining foundation PR #7 and the first-ten P0 work in PR #8.

This document records code integration, **not ten independently closed agency acceptance gates**.

| P0 | Code shipped | Verification limits/status |
| --- | --- | --- |
| 001 Wrong-person attribution | `app/evidence_gates.py`, `app/main.py` provide name-candidate and ambiguous-subject gates; no automatic verified identity | **PARTIAL** — real namesake benchmark and human subject adjudication needed |
| 002 Subject extraction drops useful names | Main P1 `app/query_parse.py` preserves original query and separates unverified clues; P0 adds `/api/cases/{id}/search-plan/subject-review` | **IMPLEMENTED_UNVERIFIED** — language/region and real-browser editing tests outstanding |
| 003 Single-pass search | `app/agent.py` adds bounded persisted follow-up research and source query deduplication | **PARTIAL** — no full automatic research worker/queue |
| 004 Answers without sufficient evidence | `app/evidence_gates.py`, main chat response conservatively abstain/identify candidate-only findings | **PARTIAL** — rule-based gating, not independent model entailment |
| 005 No claim-to-passage proof | `app/excerpts.py`, `claim_passage_proofs` bind verbatim source quotes to case evidence and content hashes | **PARTIAL** — source quote equality does not prove factual truth |
| 006 Unvalidated source relevance | Explainable question-fit and public clue conflicts in `evidence_gates.py` | **PARTIAL** — semantic ranking & gold precision@k benchmark not run |
| 007 Bias against ordinary people | Question-led `discoveryLens`, existing P1 `searchLens` plus general web, trade/education/professional classifications | **IMPLEMENTED_UNVERIFIED** — source coverage and local directories not benchmarked |
| 008 No Brave local recall | `brave_context.py` enables coarse permitted local context for public business/trade queries only, without tracking people | **IMPLEMENTED_UNVERIFIED** — provider real API & quota behavior not established |
| 009 Brave excerpts not stored | Optional bounded excerpt samples, source hashes, access-scoped endpoints; defaults to non-retention | **PARTIAL** — publisher rights and storage lifecycle unapproved |
| 010 Identity false-match rate | `identity_benchmark.py` requires annotated positive/negative pairs, source references, 2 independent reviewer IDs | **BLOCKED ON GOLD DATASET** — no empirical identity accuracy figure can be claimed |

## Conflict resolution

- Kept P1 `search_policy` source-category restrictions, full original query variants, `deferExternalSearch`, adaptive Brave pagination/site balancing, and newer search options.
- Merged P0 `discoveryLens`, saved search plans and analyst subject-review endpoints without reverting P1.
- Frontend clarification gate now fails closed on either `deferExternalSearch` or unresolved person `needsClarification`, including old response shapes.
- CI runs all original suites plus P1 and P0 clarification smoke.
- Added database tables via additive `CREATE TABLE IF NOT EXISTS`. **A tested PostgreSQL backup/restore and migration acceptance still remain open.** Never treat green SQLite mocks as a production database validation.

## Verified automated result on integration branch

- GitHub Actions: 199 pytest passed, 1 dependency warning.
- V3, V4, V7, V7.9, P1 clarification and P0 clarification Node simulated UI checks passed.
- No real Brave or Groq queries were part of CI. No independently observed namesake results. No actual browser/Playwright acceptance.
- Existing free Render Postgres expiry on 2026-11-23 remains a separate **P0-015** infrastructure risk.

## Next work

Do not close 001–010 as fully validated solely because code and CI passed. Run live authorized public-source acceptance, review provider data licensing, obtain independent annotated identity cases, and verify the database is backed up. Continue remaining issue register from P0 011–020, then 021–028; P1/P2/P3 are not automatically closed by this batch.
