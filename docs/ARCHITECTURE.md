# Architecture, engineering decisions and limits

## Goal

Address the previously reported failure mode: a previous OSINT prototype returned incorrect or mismatched personal records. The critical business capability is an investigator-controlled, evidence-backed report, not an automated dossier pretending all search results refer to one person.

## Trust boundary

1. The user provides a legitimate purpose, subject query and authorization confirmation.
2. Public-source adapters call only fixed official/public APIs. No arbitrary URL fetch, login/captcha bypass or private surveillance.
3. Raw API data is normalized into candidate Evidence records. Default is `candidate`, never automatically identified as the case subject.
4. Review classifications are recorded with a reviewer note and time. `corroborated` is a workflow classification, not an institutional credential check.
5. Remote LLM use is disabled unless the case and user explicitly opt in. Grok receives bounded source snippets and does not get uncontrolled external tool execution.
6. Exports include links, times, unverified status and limitations. The code deliberately does not compute personal criminality or trustworthiness scores.

## Candidate source data schema

```text
cases           id, title, subject_type, query, purpose, authority_confirmed, ai_opt_in
collection_runs provider, state, result_count, message, ran_at
evidence        id, case_id, provider, label, summary, source_url, source_ref,
                fetched_at, observed_at, sha256, status, reviewer_notes, reviewed_by, raw_json
users           id, username, password hash, salt, role
sessions        token hash, user_id, expires_at
audit_events    actor, action, object_type, object_id, details, created_at
```

There is intentionally **no automatic person merge**. A real entity-resolution subsystem should add separate `entity`, `source_record`, `claim`, `claim_evidence`, `link_candidate`, and `link_decision` tables, and evaluate precision against annotated cases before use.

## Integration decisions

- **Selected API adapters**: integrated (GitHub, OpenAlex, Crossref, GLEIF, Wikipedia, Wikidata, GDELT). External availability depends on provider policies.
- **Official geospatial adapters**: integrated (USGS, NASA EONET, Caltrans; TfL with registered key).
- **Source project switcher**: a UI reference/launcher. It does NOT lie about embedding or executing every upstream app.
- **3D globe**: not bundled. Licensing, tile quotas, rendering performance and provider credentials must be established before moving code across repositories.
- **Grok**: xAI Responses API with `store:false` and bounded context. Paid API and terms; no continuous background task execution.
- **Reports**: WeasyPrint HTML-to-PDF with literal text escaping and citation links.
- **Local deployment**: Python, SQLite, one web worker and static assets. Excellent for prototype portability; unsuitable for high-concurrency multi-user production without significant upgrades.

## QA and data-quality gates for a serious pilot

| Test | Required result before external use |
|---|---|
| Distinguish common namesakes | Zero incorrect automatic merges |
| Evidence citation validity | Every asserted claim must link to supporting records |
| Accuracy | Gold-set evaluation of precision, recall, abstention, mistaken identity and source coverage |
| External source failure | Never treated as negative finding |
| Dates/freshness | Provider observation time separated from fetch time |
| Cross-user access | Tenant isolation and RBAC, not present in this prototype |
| Injection | Host-allowlisting, output encoding, LLM input treated as untrusted |
| Sensitive data | Formal purpose and retention/deletion controls, additional to prototype consent confirmation |
| Provider legal terms | License, attribution, commercial use and data residency assessed individually |
| Geodata | Satellite imagery date, quality and resolution; camera publisher authorization and media freshness |

## Priority implementation beyond this demonstrable prototype

1. Harden authentication, roles, multi-tenant isolation and retention/deletion.
2. Create a proper entity/claim provenance graph and independent source-corroboration logic.
3. Source version history, admissibility/custody export and raw evidence archive permissions.
4. Add permitted Indian official company/education verification partners; analyst-assisted portal workflows where APIs unavailable.
5. Add provider health, retry/backoff, per-source quotas, background jobs and monitoring.
6. Benchmark previous OSINT Alpha failure cases against trusted known answers.
7. Add upstream geo engine adapters or optional external-service microfrontends after licensing and technical validation.
8. If desired, host approved satellite imagery through official WMTS/STAC APIs, explicitly indicating capture dates; no fictional live-HD satellite claim.
