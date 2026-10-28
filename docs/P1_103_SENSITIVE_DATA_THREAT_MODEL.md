# P1-103: Sensitive-source data flow and protection review

**Status: documented and instrumented; independent security review still open.**

### Entry points and boundaries
- Browser -> authenticated FastAPI: original questions, analyst annotations and user-entered public identifiers; token carried as HttpOnly session cookie, CSRF-protected state changes.
- Provider APIs -> backend: untrusted public metadata and excerpts. Returned candidate records may contain personally identifying details or inaccurate allegations.
- Analyst-authorized file intake -> backend: bounded original PDF/PNG/WARC data may include third-party details. Uploaded archives and bounded extracted text are stored in database tables.
- Backend -> Groq/xAI/Brave: under case consent and safety gates, selected public context may be sent to commercial providers. Consent does not imply lawful rights to process all returned content.
- Backend -> DB: evidence.raw_json, source_captures.extracted_text, research_excerpt_samples, research_messages, source_document_archives base64 binary, translation_capture_reviews, user credentials (salted scrypt hashes), session hashes and audit events.
- Backend -> reports: HTML/PDF/JSON export may copy sensitive content to analyst-controlled devices; exporter does not guarantee recipient minimization.

### Attacker model
Untrusted source injection; malicious document parser; same-name identity conflation; unauthorized case reader; stolen cookie; credential stuffing; SQL data exposure; token/API key exposure in diagnostics; hostile API dependency; backup loss; excessive data retention; compromised analyst exporting sensitive records.

### Current implemented safeguards (not an audit)
Case-level RBAC; per-user sessions; login rate caps, forced password rotation and administrator revocation; source provenance, bounded archived downloads and safe URL allowlists; explicit external consent; source-content screening; output disclaimers; parameterized database queries; child PDF renderer without provider secrets; audit events; case preservation holds.

### Unverified or absent safeguards — release blockers
**No independently verified at-rest encryption or KMS envelope encryption** for evidence; no tested database restore; no verified encrypted backup lifecycle; no phishing-resistant MFA/SSO; incomplete legal provider-use review and retention/deletion policy. Host/network TLS configuration and database filesystem protections have not been independently inspected. Existing captured records could contain incidental personal information. Browser screenshots are test fixtures only, not representative security assurance.

### Acceptance before regulated production
- Design threat-model review and vendor DPA/provider rights matrix signed by counsel.
- Independent penetration test of cross-user RBAC, cookie/session theft, CSRF, prompt injection, browser upload, stored XSS, SSRF and reports.
- KMS-managed encryption design with key rotation, access logs, re-encryption of historical sensitive data, verified restore, independent deletion/backup policies.
- Real analyst source data minimization rules, storage retention/legal hold, and incident response runbook.
- Load-tested account deactivation, password rotation, multi-worker session revocation and access audit.
- No third-party or real-person sample should be used without proper authorization.

GET `/api/cases/{case_id}/data-protection-review` returns **counts and explicit unverified controls only**, never raw evidence or private notes. This is not a compliance certificate.
