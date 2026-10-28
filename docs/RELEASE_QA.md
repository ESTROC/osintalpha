> Historical v1.0.0 QA record, not current release acceptance. Refer to [Post-152 operational acceptance](POST152_OPERATIONAL_ACCEPTANCE_20261029.md).

# Release QA Summary — OSINT Alpha Workbench v1.0.0

## Automated checks completed

- Python source compilation: passed.
- JavaScript syntax (`node --check`): passed.
- Frontend server-response render smoke (`node tests/frontend_smoke.cjs`): passed.
- Backend API/parser tests (`pytest -q`): **15 passed**.
- Authenticated API smoke run through FastAPI TestClient: login, case creation, report HTML/PDF, offline chat and audit endpoints passed.
- PDF renderer produces valid `%PDF` bytes from case HTML.
- HTML report escapes untrusted labels/descriptions.
- Unsanctioned API collector selection rejected; source failure is recorded explicitly.
- Same fetched source record does not create duplicates in the same case.
- Candidate evidence can be marked disputed and remains labeled that way in exports.

## Untested / requires live environment

- Real calls to GitHub, Crossref, GLEIF, OpenAlex, Wikipedia, Wikidata, GDELT, USGS, NASA EONET, Caltrans and TfL. The container cannot resolve external DNS.
- Grok Responses API with an actual xAI key; no key was provided.
- Real interactive browser UX and responsive screenshots. Headless Chromium navigation was blocked by administrator policy in the execution container.
- Docker image build: unavailable without registry/network access.
- Production multi-user deployment, penetration testing and regulatory data processing review.
- Performance benchmarks and empirical OSINT accuracy comparisons.
- Whole-app installation of upstream OSINT/camera/satellite repositories, which are listed as launcher references but not bundled.

## Known structural limits

- Initial single-admin model; no per-tenant isolation or self-service multi-user provisioning.
- SQLite persistence suited to private demo; PostgreSQL recommended for production.
- No background worker or continuously refreshed source catalogues.
- Candidate observations do not assert confirmed identities; no automatic person merge.
- Evidence stores a record hash but not a legally certified chain of custody or snapshot archive.
- No claimed or measured superiority over ChatGPT or commercial OSINT products.
- Public camera catalogue metadata does not guarantee real-time working feed playback.

## Required go/no-go checks before external pilot

1. Validate all chosen source API contracts, terms and required credentials on the deployment network.
2. Run a real browser regression suite across desktop and mobile.
3. Add named analyst accounts, MFA, least privilege, audit export, retention/deletion and encryption controls.
4. Validate an authorized gold dataset for false identity matches and citation correctness.
5. Commission legal review for people-data and third-party-source use and independent security testing.
