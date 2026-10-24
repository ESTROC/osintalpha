# OSINT Alpha — Investigation Workspace V2

**An evidence-led public-source research workbench.** Start with a person, organization, domain or public IP, run bounded passive public-source collectors, inspect the original record, review uncertainty and export source-linked results.

This repository is a **functional research prototype, not a complete enterprise OSINT suite or unrestricted intelligence system**.

## Live instances
Frontend: https://osintalpha-frontend.vercel.app
Backend: https://osintalpha-api.onrender.com

## What changed
- New task-first responsive analyst interface in `static/console.js` and `static/console.css`.
- Source-integrated people and company investigations preserved.
- Passive public domain DNS and IP Shodan InternetDB enrichment added.
- New `/api/capabilities` and source-linked `/api/cases/{id}/brief`.
- Clear candidate/review workflow, better AI evidence formatting, official geospatial feeds and source-vs-reference status.

See [docs/WORKSPACE_V2.md](docs/WORKSPACE_V2.md) for exact scope, quick start, deployment requirements and caveats.

## Local quick start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python run.py
```

## Quality checks
```bash
pytest -q
node --check static/console.js
python -m compileall -q app run.py
```

Security: do not commit environment secrets. Render Free SQLite data is ephemeral and not intended for sensitive or enduring investigations.
