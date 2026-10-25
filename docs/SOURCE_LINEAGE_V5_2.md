# OSINT Alpha V5.2 — Source-lineage release

## Analyst-facing delivery
- Versioned collection observations for the current planned collector, Brave public-web search, and legacy collector endpoint.
- The original stored source record is preserved when a previously tracked provider record changes.
- A changed source record resets the previous evidence-review classification to candidate and records the reason.
- An analyst-confirmed identity hypothesis that depends on changed evidence is demoted to a potential match, requiring re-review.
- Query-by-query run comparisons distinguish changed, newly returned, unchanged and not returned records. **Not returned is not deletion or removal from the internet.**
- A comparison indicates when query scope is not equal, since different queries are not a reliable same-source comparison.
- Analyst source inspector displays recorded versions and change history; Source Coverage displays differences between runs.
- Full database search/filters and pagination for the investigation registry, including author-scoped counts.
- Tests cover repeated search versions, legacy history preservation, earlier reviewer verdict resets, non-returned results, and case isolation.

## Constraints and accuracy
These features preserve snapshots of API record data, not forensic webpage archives. Provider snippets may change even when a webpage does not. Matching identifiers are candidates, not confirmed people. Search results are incomplete and may differ by time, regional indexing, pagination, quotas and provider rank. The product still does not implement autonomous, benchmarked identity resolution, high-recall general web discovery, verified source-claim entailment, permanent backup/restore or enterprise MFA/SSO.

## Configuration and durability
The optional Brave integration requires BRAVE_SEARCH_API_KEY in the Render service's protected environment. It is not considered operational without a real authenticated provider test. The PostgreSQL Free plan is temporary and should not be used for valuable investigations without upgrade and tested backups.

## QA
All public provider results in CI are synthetic. Require pytest, frontend smoke suites, deploy-ready commit and health to pass before promotion. Do not reinterpret tests as real-world search precision or recall measurements.
