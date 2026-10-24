# OSINT Alpha Intelligence Workbench

**A runnable, full-stack, evidence-first OSINT research prototype.** It is designed for authorized investigations. It is not a commercial production release and is not a replacement for licensed background verification.

## Getting started

Requires **Python 3.11 or newer** (tested here on Python 3.13). Node.js is **not** required. The frontend is authored in accessible HTML/CSS/vanilla JavaScript to run without a frontend build step.

### Windows (PowerShell)

```powershell
cd osintalpha-intelligence
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

### macOS/Linux

```bash
cd osintalpha-intelligence
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:8000** in your browser.

On first run the launcher generates a **private `.env` file** with a strong admin password and prints the credentials. Username is `admin`. Keep `.env` private; it is gitignored and excluded from the source ZIP. Use this only on your own computer or a trusted private network. The launcher deliberately binds to loopback; it does **not** expose an internet service.

Subsequent runs use the same `.env` values. If you replace the password after user creation, the stored password hash will not be updated automatically; use a fresh development database or implement a protected password-change workflow before real use.

### Optional configuration

Edit `.env` and restart:

```env
XAI_API_KEY=YOUR_OPTIONAL_XAI_GROK_API_KEY
XAI_MODEL=grok-4.7
TFL_APP_KEY=YOUR_OPTIONAL_OFFICIAL_TFL_DEVELOPER_KEY
```

The local evidence-chat mode works without any LLM key. The Grok API is **paid unless your account has credits**. The app never sends case data to Grok unless the case was explicitly created with remote-AI opt-in *and* the analyst enables Grok for the message. The API key remains on the server.

## What works in this source release

| Capability | State | Notes |
|---|---|---|
| Responsive dark investigation UI | Implemented | Sidebar, overview, cases, evidence, graph, chat, reports, geo, library, audit, settings |
| Login/session authentication | Implemented | Single initial admin; secure session cookie settings and simple login throttling |
| Authorized case creation | Implemented | Person/organization, purpose, authorization confirmation, AI opt-in |
| Official public-source discovery | Implemented connectors | GitHub, OpenAlex, Crossref, GLEIF, Wikipedia, Wikidata, GDELT; **real endpoint availability requires network testing** |
| Evidence database | Implemented | SQLite, content hash, source links, UTC timestamps, candidate default |
| Manual evidence leads | Implemented | URLs saved only; no arbitrary remote URL fetch |
| Analyst review | Implemented | Candidate, corroborated, disputed, rejected; reviewer notes |
| Candidate graph | Implemented | Visualization of case-returned leads; no unverified identity merge |
| Local case Q&A | Implemented | Deterministic keyword lookup over saved evidence, not AI research |
| Grok API | Implemented as optional | xAI Responses API, requires key and case opt-in; **not live-tested here** |
| HTML/PDF/JSON reports | Implemented | Source citations, timestamps, uncertainty caveats |
| USGS event layer | Implemented connector | Public earthquake GeoJSON; requires live network |
| NASA EONET event layer | Implemented connector | Public natural-event feed; requires live network |
| Caltrans camera metadata | Implemented connector | Publisher road-camera metadata, not universal live video |
| TfL JamCam metadata | Implemented connector | Requires official developer key |
| Interactive map | Implemented frontend | Leaflet + OpenStreetMap tiles from CDN; internet required, table works without map |
| Upstream project library | Implemented | 18 curated projects; repo/original-service launching, not all upstream apps embedded |
| Geospatial project selector | Implemented UI | Switches project documentation/launchers, **does not activate uninstalled engines** |
| Full camera relay / commercial satellite mosaic | **Not implemented** | Requires dedicated permissions, infrastructure and maintenance |
| Automatic education background verification | **Not implemented** | Needs legal authority and official providers; internet profiles are claims only |
| Full multi-tenant production security | **Not implemented** | Requires enterprise-grade auth, retention, privacy/security review, isolation and monitoring |
| Comprehensive global repository mirroring | **Not implemented** | GitHub licenses, data terms and integration safety must be checked per repo |

**The distinction matters:** An upstream repo appearing in the project library does not mean its entire codebase or dashboard is installed. Project links genuinely launch the original repo/provider; first-party normalized source adapters are integrated separately.

## App tour

1. **Investigations**: create an authorized person or organization case. Select public-source adapters and run a bounded discovery batch. Returned identities/profiles remain candidates.
2. **Evidence**: inspect labels, source URLs, timestamps and hashes. Approve/reject/dispute candidates with reviewer reasoning.
3. **Entity graph**: view evidence leads linked to the case; graph lines **do not** assert established real-world identity connections.
4. **Case chat**: use local evidence lookup without any API key, or opt in to Grok using the server key. AI suggestions must be reviewed.
5. **Reports**: download PDF, printable HTML and JSON. Reports retain unverified and rejected status instead of hiding uncertainty.
6. **Geo intelligence**: choose USGS earthquakes, NASA natural events, public Caltrans camera metadata or optional TfL JamCam listings. Switch to a table if external map scripts are unavailable.
7. **Open-source library**: filter a curated catalog and launch repositories and available original dashboards. This includes OSIRIS, God's Eye View, World Monitor, Argus and CamForge.
8. **Audit**: review authorized user actions, collections, reviews and exports.

## Architecture

```text
Browser (vanilla JS + CSS, Leaflet optional)
   |
FastAPI / auth / cases / chat / reports / API docs
   |
   +-- SQLite cases, evidence, collection runs, audit events
   +-- Fixed-host public-source HTTP adapters
   +-- USGS/NASA official event adapters
   +-- Public-authority camera metadata (Caltrans / key-gated TfL)
   +-- Optional Grok Responses API; evidence-opt-in only
   +-- WeasyPrint PDF exports
```

Every collector uses a fixed provider endpoint; the application does not turn user-supplied URLs into server-side fetch requests. Third-party responses are candidates, not truth. Source errors are stored as errors, not misreported as “no results.”

## Optional private Docker installation

Generate your `.env` first using `python run.py` (stop the local server with Ctrl+C), then run:

```bash
docker compose up --build -d
```

Docker Compose binds `127.0.0.1:8000` only and persists the SQLite database in a named volume. This Compose setup was authored but **could not be image-built in the offline environment**, so independently test it on your machine before relying on it. Do not publish port 8000 to the internet without an HTTPS reverse proxy and security hardening.

## Testing

```bash
pytest -q
python -m compileall -q app run.py
node --check static/app.js    # if Node is installed
```

At time of packaging **15 automated API/parser/security-path tests passed**, plus a dependency-free frontend render smoke test. They use mocked provider responses and test PDF generation and database-backed workflows. External API/network calls **were not verifiable from the build container** because outbound DNS was unavailable. Browser automation was blocked by the execution environment's browser policy; manual browser UX testing is needed on the deployment computer. Do not interpret the 15 tests as complete QA, penetration testing, regulatory approval or a real-source precision benchmark.

## API endpoints

After signing in, inspect interactive documentation at **`/api/docs`**.

Main routes:

- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET/POST /api/cases`, `GET/DELETE /api/cases/{id}`
- `POST /api/cases/{id}/collect`, `POST /api/cases/{id}/evidence`
- `PATCH /api/evidence/{id}`
- `POST /api/cases/{id}/chat`
- `GET /api/cases/{id}/report.pdf|html|json`
- `GET /api/geo/events?feed=earthquakes|nasa`
- `GET /api/geo/cameras?provider=caltrans|tfl`
- `GET /api/sources`, `GET /api/projects`, `GET /api/overview`, `GET /api/audit`

All case and data endpoints require authentication. Non-login mutation endpoints require the custom `X-OSINT-Alpha-Action: 1` header. Configure HTTPS and reverse-proxy security before exposure beyond localhost.

## Limits and security requirements before a real customer pilot

This demo is **not a forensically certified, multi-user, enterprise-hardened solution**.

- Replace single-admin local authentication with user provisioning, MFA, modern session/revocation controls and permissioned tenants.
- Add data encryption, retention/deletion scheduling, backups, operational monitoring and a formal threat model.
- Run upstream package scanning, secret scanning, external service data-rights review and independent penetration testing.
- Obtain permission for personal investigations and confirm the legal basis for data processing.
- Do not build personal surveillance, exposed private-camera discovery, facial recognition or account intrusion features into the platform.
- Confirm licensing for upstream code and datasets separately. In particular, World Monitor's AGPL core and God's Eye View's mixed third-party data terms do not permit an unreviewed proprietary copy-paste fork.
- For accuracy, build a verified gold-set benchmark against earlier prototype errors; no cross-source match is considered proven solely by name/username.
- For commercial imagery, cameras, social profiles, breach indicators and credential verification, use authorized providers with explicit rights.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/UPSTREAM_MANIFEST.md](docs/UPSTREAM_MANIFEST.md).

## Cloud deployment

For separated Vercel frontend / Render backend deployment, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Do not deploy with personal data using ephemeral Render Free storage.
