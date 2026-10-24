# OSINT Alpha V3 — Research Platform

## Scope
Source-linked public-person, organization, domain and IP investigations with case ownership, source history, identity clues, persisted conversations, analyst-reviewable claims and reports.

## Changes
- PostgreSQL-ready backend with SQLite local fallback.
- Admin-created analyst accounts; individual case access restrictions.
- Persistent case subject clues and heuristic (NOT verified) candidate ranking.
- Saved chat sessions, chat turns, AI source references and web-search leads.
- Durable search-run history and source-to-claim annotations.

## Data
The Render database osintalpha-research-v3 is a FREE 30-day instance expiring 2026-11-23 and cannot be considered permanent enterprise data storage. Use paid persistent storage and tested backups for real investigations. Existing ephemeral SQLite data is NOT migrated automatically.

The Render Blueprint references the database using DATABASE_URL/fromDatabase. Secret connection details never belong in source control.

## Endpoints
GET /api/users; POST /api/users (admin); GET/PUT /api/cases/{case_id}/context;
GET /api/cases/{case_id}/triage; GET /api/cases/{case_id}/search-history;
GET /api/cases/{case_id}/conversations; GET /api/cases/{case_id}/conversations/{session_id};
GET/POST /api/cases/{case_id}/claims.

## Not yet implemented
Commercial-grade multi-tenant RBAC, MFA/SSO, production backup and restore, a comprehensive web index,
automated high-confidence entity resolution, always-on source monitoring, task queue, autonomous multi-source agent loops,
satellite/AIS/ADS-B fusion, full cyber threat-feed enrichment, licensing guarantees or independently assessed security.

## QA
Run pytest -q and node --check static/console.js. Verify Render health reports database:postgres
before claiming the managed database is connected. Synthetic case tests are not live identity-research benchmarks.