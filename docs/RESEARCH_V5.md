# V5 — Research Integrity and Source Discovery

## Implemented in this release
- Corrected first-run source research previously skipped after new case creation.
- Removed immediately confirmed identity from candidate creation.
- An analyst can confirm a candidate only after an evidence-specific rationale and two distinct-provider corroborated records; this is not official verification.
- Single and bulk corroboration require specific rationale and append a review decision log.
- A completed investigation requires a substantive assessment, limitations and claim or executed research record.
- Optional Brave public-web search with explicit case-level consent, direct source URLs and metadata from provider, and query history.
- Approved-host public HTTPS source-text capture with bounded extraction, SHA-256 and saved capture history.
- Direct GitHub public-handle lookup alongside public profile discovery.
- Improved filter focus and new source capture/web discovery controls.
- Regression tests for unauthorized or irrelevant sources, capture, identity decisions and initial research execution.

## External configuration
Brave Web Search is optional. Set BRAVE_SEARCH_API_KEY privately on the Render backend to activate it. Without a key, broad web discovery shows a configuration error rather than pretending to run. Never commit provider credentials.

## What remains incomplete
These changes do not solve all 95 earlier issues. An autonomous investigative agent, calibrated identity resolution, full original-source verification, claim entailment, general web indexing at scale, continuous monitoring, enterprise MFA/SSO, backup/restore and penetration testing are not delivered.

The Render PostgreSQL Free database remains time-limited. Upgrading it and verifying backups is required before storing valuable cases.

All external provider API responses in CI are mocked. A passing unit suite is not proof of real-world accuracy or live provider completeness.