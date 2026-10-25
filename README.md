# OSINT Alpha V4 — Analyst Research Workbench

An **evidence-first public-source research workspace**, not a universal intelligence engine. The product supports source planning, bounded collection, candidate identity grouping, analyst classifications, saved research conversations and source-backed reports.

**Live frontend:** https://osintalpha-frontend.vercel.app  
**API:** https://osintalpha-api.onrender.com  
**Latest release notes:** [V4 Analyst Workbench](docs/WORKSPACE_V4.md)

## Core workflow

1. Start an authorized investigation with a subject, purpose and optional public identifying clues.
2. Preview the source-query plan (quick / standard / thorough).
3. Execute allowlisted public API searches, inspect both returned and newly saved results.
4. Filter source records, reject unrelated namesakes and group possible identity profiles explicitly.
5. Attach source-linked claims, document uncertainty and write an analyst conclusion.
6. Export the source-attributed assessment to PDF or HTML. Reopen the research later, including its saved chat history.

**Scope:** public candidate records only; no universal browsing/index, private surveillance, verified person identification or enterprise certification. Remote AI requires an API key and explicit case consent; model-proposed URLs still require independent checking.

## Storage and operations

The Render deployment uses PostgreSQL, but the free database is **time-limited**. Migrate to an adequately backed-up paid plan before retaining valuable information. Previous SQLite evidence was not automatically migrated.

## Tests

\`\`\`bash
python -m compileall -q app run.py
pytest -q
node --check static/console.js
node tests/console_v3_smoke.cjs
node tests/console_v4_smoke.cjs
\`\`\`

These are mock-backed tests and UI simulations. They do not measure identity resolution, broad public-web recall or production threat intelligence accuracy.

---

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
