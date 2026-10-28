# OSINT Alpha: post-152 operational acceptance

Date: 29 October 2026. Original numbered backlog 001-152 received engineering changes through merged PRs. Passing synthetic tests is NOT 152/152 independent acceptance or permission to handle sensitive investigative data.

## Current confirmed deployment

Backend Render LIVE at commit 607c3a76d13e997b9447a78d264b8e43a53c17a9 with green CI. The same reviewed commit was manually released to Vercel frontend deployment dpl_5RuX8f82dvNjuoFTg1c851zG2f52, READY with production domain assigned. Do not assume public anonymous browser access: Vercel deployment protection can restrict the domain.

Render PostgreSQL osintalpha-research-v3 is Free (PostgreSQL 17), AVAILABLE at inspection, expiring 2026-11-23T19:07:44Z. There is no independently witnessed backup recovery, KMS encryption or approved paid storage. Do not store irreplaceable or regulated cases before owner-authorized durability and recovery controls are ready.

## No-go conditions

- Phishing-resistant MFA / organizational SSO not installed. Password-only login remains insufficient for regulated agency production.
- Restore test, backups, storage expiry plan, encryption at rest, retention and legal-hold procedures need independent verification.
- Third-party source API permissions, licensing and personal-data rules need legal approval.
- Independent analyst user study, real citation/namesake benchmark, accessibility review, provider canaries and 24/7 incident monitoring are not complete.
- Referenced upstream tools (SpiderFoot, Sherlock, Maigret, OpenAleph, OpenCTI, ArchiveBox) are not thereby installed or authorized.

Administrator-only GET /api/admin/release-readiness provides a confidential count-free ten-gate assessment with explicit unverified state and no case records or secret values. Settings offers an administrator action to inspect it. This is an operational checklist, not certification.

## Release procedure

Use one reviewed SHA across main, GitHub unit/JS/real Chromium checks, Render LIVE and Vercel production READY. Where automatic frontend alias assignment lags, use the existing linked Vercel project to deploy only tested main SHA and verify exact aliases; do not disable SSO, change keys or provision paid services. Any substantive external client pilot requires owner acceptance of the above blockers.

The older docs/RELEASE_QA.md file documents early v1.0.0 and should not be interpreted as the current release QA.
