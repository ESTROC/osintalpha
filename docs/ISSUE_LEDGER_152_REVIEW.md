# OSINT Alpha — 152 issue independent review ledger (P0–P3)

**Base:** `ESTROC/osintalpha` main at branch creation `ad5bec605870674c6338cb413fc3d566caba1d8e`.
**Change branch:** `feature/p0-p3-correctness-audit-20261027`, **NOT merged**, no production changes.
**Source:** the user's `FULL_152_IMPLEMENTATION_TRACKER.md`; original issue titles/IDs preserved.
**CI:** 169 backend tests and 4 simulated JS smoke suites passed on a branch checkpoint; this is not live-provider/browser/identity validation.

**Current status counts:** IN_PROGRESS 14 · IMPLEMENTED_UNVERIFIED 7 · OPEN 126 · BLOCKED_APPROVAL 5.

Statuses do **not** imply a fully verified deployment. OPEN means closure cannot be proven, not necessarily that every referenced line of code is absent. Existing V8 features may address portions of open findings, but they require issue-specific acceptance and provider testing.

| ID | Priority | Original finding | Status | Evidence / remaining blocker |
|:--|:--|:--|:--|:--|
| 001 | P0 | Wrong-person attribution | IN_PROGRESS | Identity source attribution policy tightened, not benchmarked. |
| 002 | P0 | Subject extraction drops useful names | IMPLEMENTED_UNVERIFIED | app/query_parse.py preserving original plus parser tests |
| 003 | P0 | Single-pass search instead of investigation | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 004 | P0 | Answers without sufficient evidence | IN_PROGRESS | No-source narrative abstention in app/main.py; independent claim check missing |
| 005 | P0 | No claim-to-passage proof | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 006 | P0 | Unvalidated source relevance | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 007 | P0 | Coverage bias against nonprofessional people | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 008 | P0 | Disabled Brave local recall | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 009 | P0 | Fresh Brave excerpts not persisted as evidence | IN_PROGRESS | Source excerpt fingerprints saved in research_grounding, raw passages not stored |
| 010 | P0 | No independently measured mistaken-identity rate | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 011 | P0 | Zero hits easily misread as absence | IMPLEMENTED_UNVERIFIED | Source absence explicitly not treated as proof; model gate in app/main.py |
| 012 | P0 | No head-to-head benchmark | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 013 | P0 | Generic authorization purpose is prefilled | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 014 | P0 | Real provider results unverified end to end | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 015 | P0 | Free production database expires | BLOCKED_APPROVAL | Production Render PostgreSQL upgrade + backup/restore require owner approval. |
| 016 | P0 | Client privacy/security acceptance missing | BLOCKED_APPROVAL | Legal/privacy and independent security acceptance require qualified external review. |
| 017 | P0 | Brave results bypass normal evidence when Groq enabled | IN_PROGRESS | Brave context original URLs and digests recovered; source evidence workflow still incomplete |
| 018 | P0 | AI might blend different namesakes into one narrative | IN_PROGRESS | Ambiguous first-name model/source routing safeguards; no gold namesake evaluation |
| 019 | P0 | Person query with only first name is overbroad | IMPLEMENTED_UNVERIFIED | Original first-name query preserved; no automatic identity assertion |
| 020 | P0 | Primary question and collected query drift | IN_PROGRESS | Original query variants parsed and plan persisted; individual provider trace requires comparison |
| 021 | P0 | No fact classification for serious allegations | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 022 | P0 | Citation provenance breaks on later reopening | IN_PROGRESS | Session IDs, Brave source URL digests persisted; full citation-to-passage proof not solved |
| 023 | P0 | Report can omit the answer and sources shown in search | IMPLEMENTED_UNVERIFIED | Unreviewed AI reply and links included in PDF/HTML report appendix |
| 024 | P0 | AI and search quotas can stop work without predictable recovery | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 025 | P0 | No acceptance validation of analyst privileges | BLOCKED_APPROVAL | Real client analyst account provisioning and permission acceptance require owner authorization. |
| 026 | P0 | Source not found vs wrong identity not distinguished | IN_PROGRESS | No hit is not wrong-person verdict; status states still need full source taxonomy |
| 027 | P0 | Incomplete independently checked evidence coverage | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 028 | P0 | Unbounded sensitivity of remote research queries | IN_PROGRESS | Consent gating improved; full sensitive-query classification pending |
| 029 | P1 | No complete query decomposition | IMPLEMENTED_UNVERIFIED | Typed person/role/org/place/topic/handle fields added as unverified clues |
| 030 | P1 | No question type classifier | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 031 | P1 | Source router can select irrelevant APIs | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 032 | P1 | No automatic clarifying question before expensive search | IN_PROGRESS | Frontend first-name gate; clarification and iterative resume not fully validated |
| 033 | P1 | No iterative query reformulation in default workflow | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 034 | P1 | Groq browser search and Brave context are mutually exclusive | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 035 | P1 | No independent second-search corroboration | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 036 | P1 | Shallow web recall | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 037 | P1 | No site-domain balancing | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 038 | P1 | No Google-like broad person search index of its own | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 039 | P1 | Local trades/service result enrichment absent | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 040 | P1 | Indian company registry coverage weak | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 041 | P1 | India regional language/romanization support absent | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 042 | P1 | Spell variation/alias handling absent | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 043 | P1 | Occupation-specific public-record coverage absent | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 044 | P1 | Source relevance scored without context-specific negatives | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 045 | P1 | No structured query explainability on result screen | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 046 | P1 | Weak date filtering and historic-period search | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 047 | P1 | Publication/fetch date conflation risk | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 048 | P1 | No structured negative-result documentation | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 049 | P1 | Result count presented as perceived quality | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 050 | P1 | No calibrated abstention threshold | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 051 | P1 | No testable notion of complete search | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 052 | P1 | No automatic revisit on new evidence | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 053 | P1 | No first-class entity graph | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 054 | P1 | No stable identifiers across all candidate types | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 055 | P1 | No candidate-side-by-side identity workspace in main flow | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 056 | P1 | Cross-source person merges rely on human heuristics | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 057 | P1 | Shared account display names are misusable as identity | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 058 | P1 | LinkedIn not generally available as unrestricted person API | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 059 | P1 | Official employer/student institution verification scarce | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 060 | P1 | No source ownership vs publisher claim distinction | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 061 | P1 | Corroborated review can be mistaken as fact verification | IN_PROGRESS | Result explicitly labels source and analyst verification status; rigorous proof missing |
| 062 | P1 | No allegation/conflict review gates | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 063 | P1 | Copying snippets can launder SEO spam | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 064 | P1 | Web content injection test coverage limited | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 065 | P1 | Source PDF/document support narrow | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 066 | P1 | No first-class screenshot/WARC original archival | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 067 | P1 | Original URL may change or disappear | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 068 | P1 | No original quotation binding on every report claim | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 069 | P1 | Duplicate publisher syndication counted as independent leads | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 070 | P1 | No source credibility rubric or independent-source scoring | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 071 | P1 | No source/result freshness policy | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 072 | P1 | Photo attribution is not person verification | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 073 | P1 | Portfolio can mix ordinary articles with person profile candidates | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 074 | P1 | Professional affiliations lack chronology | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 075 | P1 | No counter-evidence and exclusions on main profile view | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 076 | P1 | Unverified records can dominate report length | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 077 | P1 | Initial search is blocking and non-resumable | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 078 | P1 | Search plan lost on reload | IMPLEMENTED_UNVERIFIED | case_search_plans persists full question and plan; read endpoint RBAC tested |
| 079 | P1 | Search answer provenance lost on reload | IN_PROGRESS | Research conversation + Brave provenance ledger; answer-to-claim tracking incomplete |
| 080 | P1 | Input expects case-authorization workflow for a casual search | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 081 | P1 | Initial type selection is hidden from main search | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 082 | P1 | Results screen is not a unified polished dossier | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 083 | P1 | Main nav remains visually dense | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 084 | P1 | No immediate relevant preview thumbnails for common people | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 085 | P1 | No per-claim clickable evidence drill-down | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 086 | P1 | No first-class search results sorting and filtering by question fit | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 087 | P1 | Provider and model failures not consistently shown alongside answers | IN_PROGRESS | Existing provider diagnostics, unvalidated with live failures |
| 088 | P1 | No easy correction of AI-parsed subject before case creation | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 089 | P1 | No in-case alternative candidate refinement | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 090 | P1 | Reports not automatically generated from reviewed result | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 091 | P1 | No actual end-user browser acceptance suite | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 092 | P1 | No user study with target investigators | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 093 | P1 | Brave / Groq latency can exceed proxy budgets | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 094 | P1 | Cost and search budget invisible to analyst | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 095 | P1 | No circuit breaker/backoff for upstream throttling | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 096 | P1 | No unified source health service-level target | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 097 | P1 | Single web process for heavy research and PDF generation | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 098 | P1 | Basic in-memory login throttling only | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 099 | P1 | No password reset/rotation UI for analysts | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 100 | P1 | MFA/SSO absent | BLOCKED_APPROVAL | MFA/SSO choice and identity provider configuration require owner approval. |
| 101 | P1 | Access revocation and existing sessions need acceptance tests | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 102 | P1 | Sensitive source data retention/deletion policy missing | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 103 | P1 | Insufficient data security review for stored excerpts | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 104 | P1 | Legal usage rights by provider not signed off | BLOCKED_APPROVAL | Terms and provider licensing sign-off require legal review. |
| 105 | P2 | No advanced query operators UI | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 106 | P2 | No entity alias registry | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 107 | P2 | No source jurisdiction taxonomy | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 108 | P2 | No multilingual OCR/translation pipeline | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 109 | P2 | No comparison of search runs to answer diffs | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 110 | P2 | Limited large-case pagination in evidence views | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 111 | P2 | No combined timeline | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 112 | P2 | No organization/entity relationship graph | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 113 | P2 | Geo clue map only coarse city | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 114 | P2 | Camera viewer metadata only | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 115 | P2 | Satellite imagery not integrated | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 116 | P2 | SpiderFoot not integrated | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 117 | P2 | Sherlock not integrated | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 118 | P2 | Maigret not integrated | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 119 | P2 | OpenAleph/FollowTheMoney not integrated | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 120 | P2 | OpenCTI/IntelOwl not integrated | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 121 | P2 | ArchiveBox/pywb not integrated | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 122 | P2 | Source language/date metadata incomplete | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 123 | P2 | Source adapter contracts have no live canaries | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 124 | P2 | Provider errors are not sufficiently actionable | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 125 | P2 | No per-provider caching and deduped fanout budget | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 126 | P2 | Groq model availability/version not pinned in QA | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 127 | P2 | Backend/README/docs version mismatch | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 128 | P2 | Config examples omit new key | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 129 | P2 | Versioned evidence hash not an evidentiary chain of custody | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 130 | P2 | No one-click cited source export pack | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 131 | P2 | No review assignment queue for new findings | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 132 | P2 | No relevance feedback learning | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 133 | P2 | No agency-defined investigation templates | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 134 | P2 | No analyst performance/case SLA dashboard | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 135 | P2 | Accessibility/performance baseline absent | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 136 | P2 | UI uses hardcoded HTML string assembly | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 137 | P2 | Too many requests when loading an existing case | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 138 | P2 | No duplicate use of unrelated AI answers detected | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 139 | P2 | No report-side review sign-off | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 140 | P2 | No model-output safety quality suite | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 141 | P3 | Source icons and thumbnails inconsistent | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 142 | P3 | Results visual hierarchy still dense | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 143 | P3 | Insufficient empty-state guidance | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 144 | P3 | Case titles generated from long questions | IN_PROGRESS | Existing shortened case titles; UX regression not accepted |
| 145 | P3 | No case-to-case compare UI | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 146 | P3 | Limited batch task controls | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 147 | P3 | No export preview and redaction wizard | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 148 | P3 | No client-readable methodological appendix generator | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 149 | P3 | No explicit freshness selector on first question | IMPLEMENTED_UNVERIFIED | Frontend search freshness selector exists; provider behavior not verified |
| 150 | P3 | No keyboard command palette | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 151 | P3 | No curated saved queries | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |
| 152 | P3 | No published service maintenance/status record | OPEN | No issue-specific closure evidence from this feature branch; re-evaluate against current code and acceptance tests. |

## Closure contract

For each item obtain: reproducible bug/coverage test; code+commit; role/permission tests; provider and browser acceptance when applicable; separate identity-collision ground truth; measured false positives, no-hit responses and citation entailment; security review; independent reviewer sign-off. Changing text to avoid an issue is not equivalent to closing it.

## Explicit external blocks

The **free Render Postgres database is scheduled to expire on 2026-11-23**; an upgrade, backup and restore require owner approval. API credentials and live cases must never be inserted into PRs. No independent legal/privacy penetration test or real analyst user approval was performed. Do not confuse sandbox 50-query route tests with evidence that any real person's identity has been matched.

## Recommended next phase

Prioritize P0: source-to-claim entailment, false-match benchmarks, provider live canaries, multi-stage retrieval and costly-query governance, independent human review and restore drills before expanding P2 upstream ecosystems. Real multimedia and geospatial camera layers must remain distinct from private-person tracking and require rights and timestamp proof.
