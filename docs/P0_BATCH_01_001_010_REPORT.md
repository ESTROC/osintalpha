# P0 Batch 01 — Ten-Issue Engineering and Acceptance Ledger (001–010)

Date: 2026-10-27. Source: `FULL_152_IMPLEMENTATION_TRACKER.md` original P0 descriptions.
Base: prior unmerged review branch `feature/p0-p3-correctness-audit-20261027`, SHA `1036486badfc2d36b2613c00014456a351440cf5`.
This PR branch: `feature/p0-batch01-issues001-010`. Changes NOT merged into `main`.
The ten rows below are one issue per checkpoint and are **not ten independently validated closures**.

## 001 — Wrong-person attribution
- **Changed:** `app/evidence_gates.py`, `app/main.py`. The Groq answer now receives an identity-review and question-fit gate; unreviewed name/profile hits never establish the subject's biography.
- **Test:** `test_001_two_namesakes_stay_independent` and existing `tests/test_identity.py`.
- **Status:** **IN_PROGRESS**; same-person evidence adjudication and production namesake trial remain unverified. Human identity review remains required.

## 002 — Subject extraction drops useful names
- **Changed:** previous PR's `app/query_parse.py`; new `POST /api/cases/{id}/search-plan/subject-review` preserves the full question and lets an analyst supply an auditable corrected search target *before collecting data*; explicit label does not establish identity.
- **Test:** `test_002_original_question_and_unverified_clues`, `test_002_auditable_manual_subject_correction_before_collection`, existing `tests/test_query_parse.py`.
- **Status:** **IMPLEMENTED_UNVERIFIED**; exhaustive multilingual name parsing and browser-edit workflow are not independently accepted.

## 003 — Single-pass search instead of investigation
- **Changed:** `app/agent.py` adds consented, persisted, at-most-two-step research orchestration and skips previously executed queries. `static/console.js` adds a conditional second pass on zero initial result records.
- **Test:** `test_003_bounded_multi_step_research_audited` (one- and two-step variants); source audit persists each step.
- **Status:** **IN_PROGRESS**; no background queue, full breadth-adaptive planning or live-provider timing proof.

## 004 — Answers without sufficient evidence
- **Changed:** `app/evidence_gates.py` and `app/main.py` with conservative no-source abstention and candidate-only mode for unconfirmed people. Existing model clarification remains possible.
- **Test:** `test_004_no_evidence_no_biography`, `test_no_evidence_assertion_abstains_without_hallucinated_biography`.
- **Status:** **IN_PROGRESS**; rule-based sufficiency and no independently calibrated claim-level evidence threshold.

## 005 — No claim-to-passage proof
- **Changed:** `claim_passage_proofs` relational table and `POST/GET /api/cases/{id}/claim-passages` in `app/excerpts.py`. Requires same case, same evidence, actual extracted source text, exact quote substring, matching cryptographic content digest, and non-rejected source.
- **Test:** `test_005_claim_binding_rejects_unrelated_sources_and_matches_exact_text`.
- **Status:** **IN_PROGRESS**; a text match does not prove interpretation, factual truth, author identity or semantic entailment.

## 006 — Unvalidated source relevance
- **Changed:** `app/evidence_gates.py`: question/subject overlap with explicit contradictory city, organization or public-handle flags; tool output identifies candidate coverage rather than probability.
- **Test:** `test_006_contextual_negative_outweighs_name_hit`.
- **Status:** **IN_PROGRESS**; semantic reranking benchmark on gold-labeled data remains open.

## 007 — Coverage bias against nonprofessional people
- **Changed:** `app/smart_search.py`: choose `general`, `trade`, `education`, `professional` web search based on the entire question; `static/console.js` passes the backend lens to Brave Web Search.
- **Test:** four cases under `test_007_backend_discovery_lens`, plus existing broad-scope tests.
- **Status:** **IMPLEMENTED_UNVERIFIED**; local registries, multilingual public sources, web recall and real tradesperson coverage have not been measured.

## 008 — Disabled Brave local recall
- **Changed:** `app/brave_context.py` now opts into documented `enable_local=true` and `X-Loc-City/X-Loc-Country` only when an analyst supplied public city context AND query is about public businesses/trades, not the location of a person.
- **Test:** `test_008_business_only_local_recall` verifies request body and headers for a trade question and no city-header leak for unrelated person query.
- **Source:** Brave LLM Context documentation (2026) https://api-dashboard.search.brave.com/documentation/services/llm-context.
- **Status:** **IMPLEMENTED_UNVERIFIED**; upstream real ranking improvement, quota and provider latency not measured.

## 009 — Fresh Brave excerpts not persisted as evidence
- **Changed:** previous PR keeps immutable Brave URL, query, date, source title and excerpt digest. This PR adds a **separate explicitly opted-in 160-character searchable excerpt sample** table and access-scoped retrieval endpoint. Default retention is OFF; never infer publisher authenticity. Stored samples and case records must follow a retention/licensing policy.
- **Test:** `test_009_public_excerpt_samples_require_explicit_opt_in`.
- **Status:** **IN_PROGRESS**; complete reproduced pages, legal storage rights and lifecycle acceptance not yet checked.

## 010 — No independently measured mistaken-identity rate
- **Changed:** `app/identity_benchmark.py` evaluates 20+ independently sourced and dual-reviewed reference pairs; reports false link signals, abstention, wrong name signals, and both positive and negative examples, refusing malformed or one-reviewer entries. Software cannot certify reviewer independence.
- **Test:** `test_010_reference_metric_refuses_fake_ground_truth` using explicitly synthetic positive/negative labels.
- **Status:** **BLOCKED_APPROVAL** for an accepted consented reference dataset and independent evaluation; **no real-world false match rate can be claimed** yet.

## Cross-cutting validation
- All remote external provider network responses in current CI use synthetic stubs or mocks. No live Brave/Groq, genuine named person investigation, licensed publisher image capture, real-browser Playwright or Render schema rollout has been validated in this branch.
- No production secret was read, printed or changed. No live database was migrated.
- Two new schema tables (`claim_passage_proofs` and `research_excerpt_samples`) are introduced in `app/db.py`; owner and database reviewer must approve a deployment/migration before merge.
- After each P0 fix, rerun `pytest -q`, all console smoke tests and check sources/citation correctness. A passing pytest run is not provider or independent identity evidence.
- Outstanding safety: source rights/licensing, structured quote entailment, independent identity benchmarks, provider SLAs, full privacy/security acceptance and Render PostgreSQL backup/restore.

## Next batch
Batch 02 = P0 **011–020**, on a separate stacked review branch after this branch's final checks. No automatic merge into main.
