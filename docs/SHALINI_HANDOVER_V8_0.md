# OSINT Alpha V8.0 — Unified analyst experience and scoped handover

Release: 27 October 2026
Scope: UX, dynamic source routing, combined Brave Search + Groq, map visibility and candidate media provenance.

## Delivered

**No personalized static example in the public search placeholder.** Removed the named individual/employer demo query from the landing search and the hardcoded assumptions that "Indian Navy" and "cybersecurity" are proven attributes of a searched subject. The source router treats profession and employer as analyst-supplied clues or literal model-extracted possibilities; a search topic is not a verified biography.

**Responsive mission-control UI.** Reduced headline sizing, constrained all page widths, improved wrapping and mobile form layout, removed hardcoded administrator username from login, gave the main search a restrained orbital background and added a real Leaflet/OpenStreetMap global map section. USGS earthquake observations are pulled from the existing public-source API only when the analyst selects **Load USGS events**. Geographic observations have publisher provenance and are not the subject's coordinates.

**Backend-first intelligent workflow.** Search submission invokes the backend's constrained Groq-assisted public-source planner when explicitly authorized, otherwise a generic explainable fallback. The backend chooses only allowlisted compatible structured public APIs, and accepts neither guessed identity matches nor invented professional affiliations.

**Both Brave products and Groq in one research flow.** The initial search now issues a Brave Web Search request to preserve original URL candidates whenever a web key is present; in consented Groq mode it also retrieves Brave LLM Context excerpts for fresh source-grounded synthesis, in addition to selected structured source records. They use the existing Render-held secrets, and independent provider errors are visible in the result instead of being treated as success. A Brave LLM Context quota/entitlement failure downgrades visibly to analysis over saved records.

**Analyst result UI.** Displays original sources, provider health states, human review statuses, candidate GitHub-hosted account avatars when actually supplied by a publisher, and a separate public-city map preview if the case has an explicit coarse public city clue. Personal whereabouts, guessed home coordinates, face matching and live-person camera tracking are not supported.

**50 synthetic investigation questions with a real isolated analyst login** exercised as an automated integration test using FastAPI TestClient, a temporary database and an intentionally test-only credential. The cases span trades, students, public events, businesses, researcher contexts, public domain/IP records, weather and official publication searches. Tests check creation, safe provider routing, source boundaries, administrative separation and case ownership. No upstream people were queried, no billable tokens were consumed and no production credentials were accessed.

## Critical acceptance gates still OPEN

1. **Real provider benchmarking**: Brave Web Search and LLM Context access/quotas; Groq real inference and response structure; measure response relevance, source coverage, cost and latency in a controlled non-sensitive trial. Automated mocks cannot prove factual answer accuracy.
2. **Browser E2E**: Playwright or human scripted evaluation on desktop and mobile, including visually inspecting responsive viewport and map tiles. CI's Node tests simulate the browser DOM, not a real running browser.
3. **Source reliability**: adjudicate 50 real consented/publicly documented tasks independently, including namesakes and no-result cases; score unsupported claims and correct citations.
4. **Production analyst account**: create a separate analyst user in the protected administration UI and verify the exact intended case permissions before sharing access. A production login/password has not been created by this release.
5. **Database**: Render Postgres `osintalpha-research-v3` free instance expires 2026-11-23. Upgrade and test a restore before using for valuable client work.
6. **Licensed media and geocoding**: OSM public tile/Nominatim policies, account-avatar publication rights and source freshness; do not equate camera coverage with presence of an individual.
7. **Feature limits**: advanced source projects in the upstream manifest are **references** until actually integrated and separately tested. A generalized world-scale real-time camera network and 100%-accurate identity resolution are not implemented.
8. **Security/privacy**: penetration assessment, provider spending caps, secrets rotation, MFA/recovery, quota throttles, malicious source/prompt injection tests, data retention and client terms.
9. **Historical 95-item audit**: requires a fresh numbered item-by-item acceptance comparison. New code/tests do not certify all items are closed.

## Shalini handover

Use the production login (separate restricted analyst account), ask one question, confirm authorization, optionally enable AI-assisted routing, inspect the AI answer, compare original URLs in Sources and record contradictory/unsupported information. Only source-backed observations with adequate independent review should appear as findings in a client report.

A failing source should show an error; an unsupported person claim should be labeled unknown or unverified. Avoid relying on internal success-count metrics as precision/recall. The image preview identifies the **public account source**, not the person. The city map plots a **user-supplied region clue**, not a residential or live personal location.

## Files

- `app/smart_search.py`: generalized, consented backend source routing.
- `app/brave_context.py`: existing bounded source-grounded LLM context.
- `static/console.js` and `static/console.css`: responsive search, merged source diagnostics, map and imagery.
- `tests/test_analyst_50_questions.py`: 50-query isolated analyst session and permission checks.
- `tests/console_v7_9_smoke.cjs`: Brave + Groq combined workflow assertions.
