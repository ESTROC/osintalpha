# REVIEW_FOR_CHATGPT — OSINT Alpha P0–P3 branch, independent final audit

**Review type:** adversarial independent engineering QA. **Do not merge this branch or claim any 152 issues closed based only on this note.**

## Source of truth and branches

- Repository: https://github.com/ESTROC/osintalpha
- Feature branch: \`feature/p0-p3-correctness-audit-20261027\`, created from main \`ad5bec605870674c6338cb413fc3d566caba1d8e\`.
- Original requirement source: user's \`FULL_152_IMPLEMENTATION_TRACKER.md\` and \`OSINT_ALPHA_CLAUDE_EXECUTION_MASTER_BLUEPRINT_2026-10-27.md\` from the user's Library.
- **Current 152-item issue-by-issue evidence register:** \`docs/ISSUE_LEDGER_152_REVIEW.md\`. All 152 original issue names represented, with unverified/open status where completion cannot be shown.
- User explicitly directed **no production merge without approval**. Treat this as a review PR only.

## Concrete code changes

1. **app/query_parse.py** is the user's supplied 312-line original-preserving unverified-identity parser, adapted via patch to the current main. It separates name, topic, role, organization, region, handles and query variants; never asserts identity. Additional generic civic terms reduce false first-name parses.
2. **app/smart_search.py** uses that parser; full original question and parsed plan are persisted to \`case_search_plans\`, retrievable by \`GET /api/cases/{case_id}/search-plan\` under existing RBAC. Unclarified person identities do not trigger automatic paid Groq router selection.
3. **static/console.js** restores saved search plans after reload and shows an explicit source abstention/clarification screen for single-given-name person cases *before* default-source collection and Brave/Groq calls. The analyst must supply a more discriminating public clue before continuing.
4. **app/db.py** creates \`case_search_plans\` and \`research_grounding\`, referentially scoped to cases/sessions. **This is schema addition; deploying will create tables. Do not merge before deployment/database approval.**
5. **app/main.py** persists per-source HTTPS URL, title, source date, search query, retrieval time, and SHA-256 of a Brave extracted snippet to \`research_grounding\` **without storing the third-party snippet text**. Adds access-scoped \`GET /api/cases/{id}/grounding\` endpoint. SHA-256 is a repeatable fingerprint, *not* authenticity or author verification.
6. **app/main.py** guards remote model outputs that assert facts when no usable saved source, fresh Brave source, or active browser-search source was available. It preserves conversational/clarifying responses and labels remote synthesis as unverified.
7. **app/main.py** report appendix includes the original user search question, latest saved unreviewed AI answer, original source links and disclaimer in HTML/PDF, escaping user/source text.
8. Added synthetic tests for source-grounding metadata, cross-analyst access protection, empty-evidence abstention, source/plan reloading and report HTML escaping. Added no-Brave/no-Groq frontend clarification smoke regression.

## What these do **not** solve

- No independent source claim-to-passage **entailment** measurement, real-world identity/name collision benchmark, honest overall precision/recall, or proof that matching names represent the same person.
- No generalized iterative search orchestration with job queue/resume across Brave/Groq/real source APIs.
- No live production Brave/Groq permission, quota, latency, geographic source quality or licensed media tests.
- No real-browser Playwright screen-level regression beyond simulated JS smoke tests.
- No backup/restore drill or Postgres upgrade; live Render free database expiry is 2026-11-23.
- No penetration test, statutory privacy DPIA or provider intellectual-property/license sign-off.
- No complete P0/P1/P2/P3 implementation. See ledger. Reopen any "implemented_unverified" row until independent validation.

## Adversarial checks for the reviewer

- Run all pytest and Node tests at the feature branch head; compare to the base commit and identify false green tests.
- Test "Ayush cybersecurity Indian Navy", bare first names, full common names, and civic/event headlines including "City government planning consultation publication". Verify first-name false positives and browser UI content persistence.
- Try citations with correct URL but claims unsupported by source text. Confirm this is **still a known gap** and not marked fixed.
- Verify an analyst without case permissions cannot fetch source digests or saved search plans; test session reuse and revoked users.
- Test Unicode, hostile HTML, nested/double encoding, very long input, copied source prompt injection and quote/excerpt hash collision assumptions.
- Test that externally retrieved URLs and snippets are never treated as approved identity evidence by default.
- Test no hits, upstream rate limits, partial connectivity, missing credentials, manual provider selection and unknown company/person types.
- Confirm report appendices do not imply an AI-generated answer is a signed-off analyst finding.
- Validate that new schema creation is safe for PostgreSQL/SQLite. **Any live migration requires approval**; no production data touched here.
- Before commercial use, conduct a real independent security + privacy review.

## Evidence status

This feature branch's GitHub CI exercises synthetic pytest and simulated console Node smoke suites. The suite's exact passing count is documented by GitHub Actions. Automated passing tests are **not** evidence of provider uptime, correct identity matching, human source verification or client acceptance.

The user's transferred Claude \`p0-parse-slice.patch\` originally had 12 pure-stdlib parser tests passed with an offline stand-in runner, but did NOT have full app tests. This branch integrates it into the real repo with CI. Original independent file provenance: \`REVIEW_FOR_CHATGPT.md\` user upload.

## Approval gates

- User: explicitly approve production branch merge and **any** Render schema change/backup/upgrade.
- Legal/privacy: license terms, data retention and processing purpose, appropriateness of country/locality data, model transfer rules.
- Owner: MFA/SSO decision; secure analyst invitation/provisioning, not test-only credentials.
- Independent reviewer: real Brave/Groq and real-browser acceptance with approved synthetic or documented public subjects.

**Never claim P0/P1/P2/P3 are all solved without closure-grade evidence for each of 152 issue IDs.**
