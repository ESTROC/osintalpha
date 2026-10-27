# P1 Batch 01 — Original issues 029–038

Date: 2026-10-27
Code base: production `main` at `ad5bec605870674c6338cb413fc3d566caba1d8e`
Branch: `feature/p1-batch01-029-038`
Requested disposition: review, test, merge passing code to `main`; independently validate behavior before certifying any original issue as closed.

**Source of issue names and repair intentions:** `FULL_152_IMPLEMENTATION_TRACKER.md` issues 029–038.
**Important:** tests are synthetic and mocked, not measurements of live Brave/Groq, web completeness, source authenticity or real person matching.

| Issue | Original finding | Code evidence | Test evidence | Closure status |
|---|---|---|---|---|
| 029 | No complete query decomposition | `app/query_parse.py`, `search_policy.plan_question`: original preserved with tentative name, role, topic, organization, region and handles | `tests/test_query_parse.py`, `test_029_030_taxonomy_and_original_query` | **PARTIAL**: explicit event/date roles and reversible analyst plan editing still incomplete |
| 030 | No question type classifier | `search_policy.question_type`: approved finite taxonomy of eight task categories plus general task | `test_029_030_taxonomy_and_original_query` | **IMPLEMENTED, NOT REAL-WORLD ACCEPTED**: classification needs gold query taxonomy benchmark |
| 031 | Source router can select irrelevant APIs | `search_policy.permitted_sources` filters CATALOG by task and supported subject type; model cannot override rule | `test_031_model_cannot_override_task_specific_source_allowlist` | **PARTIAL**: source utility not learned from measured relevance |
| 032 | No automatic clarifying question before expensive search | `smart_search.start_search` emits `deferExternalSearch` for single given-name subject; `static/console.js` stops Brave/Groq/structured collection | `test_032_first_name_stops_expensive_groq_routing`, `console_p1_clarification_smoke.cjs` | **PARTIAL**: common complete names and ambiguous organization names may still pass |
| 033 | No iterative query reformulation in default workflow | `v5.make_queries` plus `web_discovery(adaptive=True)` issue bounded task-specific query variants until coverage threshold or budget | `test_036_brave_pages_with_realistic_mocked_responses`; baseline UI smoke | **PARTIAL**: not a fully feedback-driven multi-provider agent |
| 034 | Groq browser search and Brave context mutually exclusive | `POST /api/cases/{id}/cross-engine-check` explicitly invokes Groq browser search in a subsequent, consented turn after a saved source-linked chat | `test_034_035_cross_engine_requires_consent_and_preserves_caveat` | **PARTIAL**: optional separate turn, model/tool quota and live provider behavior unverified |
| 035 | No independent second-search corroboration | Returns source/publisher overlap from two separately sourced result sets with `independentCorroborationVerified=False` | Same regression; manual original pages remain required | **PARTIAL**: domain overlap is not verified independent ownership or factual corroboration |
| 036 | Shallow web recall | `WebSearchInput.pages` up to 3, Brave documented offset paging, honors `more_results_available`, max 3 task variants with conditional early stop | `test_033_036_037_publisher_diversity_and_stop_budget`, `test_036_brave_pages_with_realistic_mocked_responses` | **PARTIAL**: live recall/precision measured against benchmark missing; bounded quotas |
| 037 | No site-domain balancing | `publisher_group`, `balance_results` with registered-looking hostname grouping and domain caps applied before persistence | `test_033_036_037_publisher_diversity_and_stop_budget` | **IMPLEMENTED, NOT REAL-WORLD ACCEPTED**: unrelated publishers may share corporate ownership; some registrable domains require better PSL logic |
| 038 | No Google-like broad person search index of its own | `GET /api/cases/{id}/local-source-index` searches prior stored, authorized case evidence and explicitly says `hasIndependentIndex=False` | `test_038_local_index_is_case_scoped_and_not_a_global_web_index` | **OPEN**: no independent global public web index or licensed alternative feed exists |

## Validation gates

- GitHub Actions: run Python suite and existing/new Node simulated UI smoke on this branch, then again after merge.
- Independent source relevance: collect representative authorized queries, validate profile namesakes and compare source recall@k, precision@k, freshness, cost and query budget to baseline.
- Groq built-in browser search officially requires a compatible GPT-OSS model and cannot return structured JSON in the same tool-calling request; this release keeps it a separate opt-in round: https://console.groq.com/docs/tool-use/built-in-tools/browser-search
- Brave Web Search `offset` is a page offset, 0–9; `count` max 20. The endpoint now honors publisher `more_results_available` to avoid wasted requests: https://api-dashboard.search.brave.com/app/documentation/web-search
- No new database schema, migration, production secret, or identity claim was introduced in this batch. No one has asserted that independent browsing was actually run with real provider keys.
- This batch **does not merge or close prior P0 PR #7/#8**; those require separate conflict and operational review.
- Remaining P1 issues 039–104, P2 105–140, P3 141–152 are not yet implemented in this batch.

## Developer handover

Review `app/search_policy.py`, `app/smart_search.py`, `app/v5.py`, `app/cross_engine.py`, `app/local_index.py`, UI state handling, and `tests/test_p1_batch01.py`. The human reviewer should verify the fixture's assumptions and prevent domain count from being misrepresented as independent corroboration.

**No issue is marked independently closed based solely on synthetic CI.** Code completion statuses above are strictly narrower.
