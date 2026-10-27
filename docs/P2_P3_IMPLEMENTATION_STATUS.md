# V8 P2/P3 issue status — 27 October 2026

Source of truth: the original OSINT Alpha 152-item agency register, IDs 105–152. Code implementation and CI are not a claim of independent live-provider or browser acceptance.

Legend: C = code present with mock regression checks; P = partial implementation; B = blocked by required third-party rights, hosted services or credentials; O = open.

| ID | State | Source code status and remaining acceptance |
|---:|:---:|---|
| 105 | P | Advanced site, phrase, exclusion, locale and freshness filters; preflight preview absent |
| 106 | C | Typed case aliases with URL and rationale |
| 107 | P | Source coverage taxonomy; full jurisdiction validation absent |
| 108 | P | Manual translation notes; no actual OCR/machine translation |
| 109 | P | Saved answer text diff; no structured claim comparison |
| 110 | C | Paged evidence API and modular Next/Previous review |
| 111 | P | Source dates timeline; real-world events not verified |
| 112 | P | Sourced, reviewable relationship edges; no graph viewer |
| 113 | P | Existing city clue map; no verified organization map |
| 114 | P | Optional official TfL public stills; frame timestamps unverified |
| 115 | P | Dated NASA GIBS world overlay; tile availability not live-tested |
| 116 | B | SpiderFoot not installed; site policy and isolated runtime required |
| 117 | B | Sherlock not installed; username false positives and site terms unresolved |
| 118 | B | Maigret not installed; compliant site list and rights unresolved |
| 119 | B | OpenAleph/FollowTheMoney not installed; migration/hosting and license gate |
| 120 | B | OpenCTI/IntelOwl not installed; credentials, infrastructure and permissions |
| 121 | B | ArchiveBox/pywb not installed; WARC rights/storage/replay required |
| 122 | P | Brave locale metadata and source dates; upstream coverage incomplete |
| 123 | P | Opt-in real adapter canary; no daily scheduler or alerts |
| 124 | P | Provider errors already surfaced; retry-after/last-success pending |
| 125 | O | Bounded fanout exists, shared scoped cache and quota policy absent |
| 126 | P | Groq configuration inspection; real model compatibility QA absent |
| 127 | P | README updated; older historical QA docs remain historical |
| 128 | C | Private Brave and Groq config documented and blueprint keys declared |
| 129 | P | Explicit integrity limitations; no forensic custody system |
| 130 | P | Reviewed metadata evidence pack; original signed snapshots missing |
| 131 | C | Opt-in suggested review tasks for disputed/unreviewed sources |
| 132 | P | Persistent source relevance feedback; model not retrained |
| 133 | P | Built-in and user-private search recipes; team versioning absent |
| 134 | P | Workload/error dashboard endpoint; no measured source precision or SLA |
| 135 | P | Semantic advanced UI and fewer startup requests; browser QA absent |
| 136 | P | Separate agency.js module; console.js still monolithic |
| 137 | C | Case boot now lazy-loads specialist modules |
| 138 | P | Source citation reuse report; not true independent corroboration |
| 139 | P | Review signoffs with stale digest; PDF downloads not hard-gated |
| 140 | P | Expanded privacy/access synthetic tests; benchmark corpus absent |
| 141 | P | Uniform provider labels in agency source cards; real thumbnails absent |
| 142 | P | Advanced tools separated from four main tabs; usability test needed |
| 143 | P | Actionable new pagination empty state; legacy guidance incomplete |
| 144 | C | Short UTC-dated case title generated |
| 145 | P | Authorized case source overlap comparison; not semantic claim diff |
| 146 | C | Audit-logged batch task transitions; batch final approval forbidden |
| 147 | P | Redacted JSON preview and reviewed pack; not redacted PDF wizard |
| 148 | P | Search-methodology endpoint; not appended to legacy PDF |
| 149 | C | Brave locale and freshness controls on first question |
| 150 | P | Ctrl/Cmd+K commands in agency workspace; not sitewide |
| 151 | P | Owner-scoped reusable recipes; full revision/version UI absent |
| 152 | P | Authenticated ops-status endpoint; public uptime/maintenance page absent |
## Major acceptance gates

- The 116–121 upstream engines are NOT installed simply because a manifest links to them. Consent, licensing, site policy, isolation, hosting and source-specific validation remain mandatory.
- Source images, NASA tiles and public cameras do not identify anyone or establish live personal whereabouts. Public imagery date and resolution must be checked from the publisher.
- Keyless TfL anonymous API is rate-limited, with no guarantee the publisher offers a valid current still. Live provider acceptance remains required.
- Provenance hashes and JSON metadata exports are NOT forensic chain of custody, original-page WARC or legal certification.
- Human-approved findings, privacy/cross-user permission tests, backups and actual search quality benchmarks remain essential before client use.
- Main search remains four tabs; agency specialist actions are in a separate authenticated optional page linked under More analyst tools.

## Key code paths

app/agency_ops.py, app/db.py, app/smart_search.py, app/v5.py, app/brave_context.py, app/connectors.py, static/agency.js, static/agency.html, static/console.js, tests/test_agency_ops.py.
