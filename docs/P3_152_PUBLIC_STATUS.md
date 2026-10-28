# OSINT Alpha pilot service status

GET `/status` renders the public, server-generated API/database response and latest explicitly published operator notice. GET `/api/public/status` returns a machine-readable release, observed source-request aggregates, and notice history. POST `/api/admin/service-notices` requires an authenticated administrator and CSRF action confirmation. Notices are append-only with recorded publication time; no raw provider request details, API keys, people queries or personal identifiers should be entered.

A successful request is only a point-in-time backend/database check. **It is not continuous monitoring, SLA evidence, a verified backup or an assertion that external providers are healthy.** If no provider observations exist, provider status is unknown. Human published notices are distinguishable from independent monitoring.

Release source: `app/release.py`. For external incidents, owners should publish a dated notice, verify source failures from authenticated telemetry, document recovery and mark resolved without erasing prior notices. Production legal/security acceptance remains unresolved.
