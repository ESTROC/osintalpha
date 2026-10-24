# OSINT Alpha — Investigation Workspace V2

This release prioritizes actual, bounded functionality over product claims.

## Start an investigation
1. Sign in, use Workspace, choose People, Organizations, Domains or Public IPs.
2. Enter a specific query and an authorization/purpose statement.
3. The application creates a case and attempts up to five matching public-source adapters.
4. Open Overview for source health, Evidence for candidate records, AI briefing for source-grounded summaries and Reports for export.
5. Re-run sources as required and record corroboration decisions with reviewer notes.

## Integrated connectors
- People: GitHub, OpenAlex, Crossref, Wikipedia, Wikidata (GDELT also available via source catalog for person/organization).
- Organizations: GLEIF, GitHub, Wikidata, Wikipedia, GDELT.
- Domains: Google DNS-over-HTTPS passive A/MX/NS lookups.
- Public IPs: Shodan InternetDB passive host-observation metadata, CVE *references*, hostnames and ports.
- Geospatial: USGS earthquake events, NASA EONET natural events, Caltrans and TfL official camera metadata.

**These are candidates.** Account profiles and matching names do not prove identity. InternetDB's reported ports and CVE references can be stale and do not demonstrate presently exploitable vulnerabilities. This app does not actively scan networks.

## Included in API
`GET /api/capabilities` and `GET /api/cases/{id}/brief` provide an accurate feature inventory and deterministic case summaries. Existing case, collection, review, report and chat endpoints are preserved.

## AI
The offline option uses deterministic evidence lookup. GroqCloud and xAI Grok operate only with the relevant server-side key and explicit case opt-in. They answer from stored evidence; they cannot silently browse unknown sites. Treat every AI output as a draft for analyst verification.

## What is not implemented
- Sherlock, Maigret, OSIRIS, World Monitor, SpiderFoot, IntelOwl, Argus, CamForge, OpenCTI and other referenced open-source engines are not deployed or fused. The Source integrations screen labels them **Reference only**.
- No universal identity verification, face recognition, private cameras, account intrusion, paid dataset access, or unsupported automated threat verdicts.
- No multi-tenant RBAC, durable database for Render Free, proprietary licensed data platform or production security certification.

## Deployment
GitHub main automatically builds Docker on Render (backend) and the `static/` root on Vercel (frontend). The Vercel same-origin Node API proxy uses `OSINTALPHA_BACKEND_URL` to reach Render. `GROQ_API_KEY` and `XAI_API_KEY` belong **only on the Render backend**.

Render Free SQLite data is ephemeral: demo use only. Do not store sensitive personal investigations until persistent storage, security hardening, appropriate permissions, audit compliance and source licensing are completed.

## QA
Run `pytest -q`, `python -m compileall -q app`, `node --check static/console.js`, and `node --check static/app.js`. Automated collector tests mock remote responses; source API uptime is not guaranteed.
