# OSINT Alpha — Public-Source Investigation Workbench

**Release branch:** V8.0 P2/P3 agency tools. **Stable baseline:** V7.9.  
**Live frontend after a reviewed merge:** https://osintalpha-frontend.vercel.app  
**Backend:** https://osintalpha-api.onrender.com  
**Agency operations:** \`/assets/agency.html?case=<authorized-case-id>\` (analyst login required)  
**Engineering and remaining issues:** [P2/P3 implementation status](docs/P2_P3_IMPLEMENTATION_STATUS.md).

## Intended analyst workflow

1. Log in using your assigned analyst account; administrators should not share credentials.
2. Search a public-source research question with a legitimate authorized purpose.
3. Optionally consent to Groq and Brave and choose an explicit search locale, date range, original phrase, exclude term or public site.
4. Review *candidate* public records, original links, source dates and provider errors; distinguish namesakes.
5. Ask targeted follow-up questions and use human-review controls for sources, claims and uncertain relationships.
6. Use **More analyst tools → Advanced agency toolkit** for a dated timeline, typed aliases, relationships, saved procedures, paginated evidence, review task suggestions, redacted export previews, sign-off and case comparisons.
7. Export source-linked assessment only after explicit review. Saved-source metadata hashes are **not** a certified chain of custody.

The main case UI has four tabs. Specialist functions remain optional.

## Connected sources versus references

Actual first-party connectors currently query GitHub, Stack Overflow, OpenAlex, Crossref, GLEIF, Wikipedia, Wikidata, GDELT and optional public event/road-camera feeds. Brave Search and Brave LLM Context require a private backend API key; Groq responses require its own private key and case consent.

Public TfL JamCam discovery uses the official anonymous low-quota API or a configured developer key. Camera stills load **only after request**, with original-publisher attribution and **no independently verified per-frame timestamp**. A dated NASA GIBS satellite layer is available in World Intelligence, with date, cloud and availability caveats. Neither is a personal tracking feature.

SpiderFoot, Sherlock, Maigret, OpenAleph, FollowTheMoney, OpenCTI, IntelOwl, ArchiveBox and pywb are **not deployed upstream engines**. They need individual security, licensing, site-policy, hosting and acceptance checks; reference links are not API integration.

## Configuration

See [\`.env.example\`](.env.example) and [\`render.yaml\`](render.yaml).

- Required: \`OSINTALPHA_ADMIN_PASSWORD\`, a PostgreSQL \`DATABASE_URL\` for durability, HTTPS secure-cookie configuration.
- Optional server secrets: \`GROQ_API_KEY\`, \`BRAVE_SEARCH_API_KEY\`, \`XAI_API_KEY\`, \`TFL_APP_KEY\`.
- Optional model setting: \`GROQ_MODEL=openai/gpt-oss-120b\`. This value is a known default, **not** a verified long-term provider compatibility guarantee.
- Keys never belong in frontend files, reports, GitHub commits, or chat messages.
- The free Render PostgreSQL instance is scheduled to expire **2026-11-23**. Upgrade and test a backup restoration before storing valuable work.

## Verification

\`\`\`bash
python -m compileall -q app run.py
pytest -q
node --check static/console.js
node --check static/agency.js
node tests/console_v3_smoke.cjs
node tests/console_v4_smoke.cjs
node tests/console_v5_smoke.cjs
node tests/console_v7_9_smoke.cjs
\`\`\`

Passing mocked tests and simulated UI checks does not establish source truth, independent identity accuracy, live provider availability or agency-grade security. The application is an evaluation platform; do not make high-impact conclusions without original evidence and human authorization.

## What remains

Read [P2/P3 status](docs/P2_P3_IMPLEMENTATION_STATUS.md) and [the comprehensive agency register](docs/SHALINI_HANDOVER_V7_9.md). External OSINT services, OCR, forensic WARC archives, certified chain-of-custody, continuous provider uptime, complete mobile browser QA and licensed data contracts remain distinct follow-up work.
