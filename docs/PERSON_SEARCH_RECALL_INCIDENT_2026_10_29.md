# Public person-search recall incident — 29 October 2026

## Symptom
The analyst gave a complete natural-language description of a named person, cyber-security work connected to a naval organization and educational institution. The app returned 10 stored same-name profiles in unrelated roles and wrongly suggested that the queried work had no relevant public record.

A separate public search surfaced an indexed LinkedIn post from an account with the named person's display name that **self-reports** a naval cybersecurity internship. This is a matching **public lead**, not independent employer verification. The education clue was not independently established by that post.

## Confirmed root causes in previous V8/branch UI
1. Default `/web-discovery` call requested `depth:1`, executing only the original broad query, not generated targeted publisher searches.
2. Search country defaulted to `US`, imposing an unrequested geographic bias. Updated to `ALL` for worldwide Web Search; LLM Context omits country in this mode (provider's own default may apply).
3. The question planner quoted an entire multi-clause question instead of an independently parsed, **tentative** person's name plus separate original employment and education clues.
4. Lexical retrieval filled the context up to 35, even with unrelated same-name profiles. The UI called this `relevant stored records`, an unsupported relevance claim.
5. A model with `needs_disambiguation=true` could still categorically state that no matching record existed, even when a public-index candidate overlapped the name and explicit work clues.
6. `Groq browser_search` and `Brave LLM Context` were mutually exclusive in one LLM call, even though Brave Web Search, Brave LLM Context and Groq synthesis together formed a usable pipeline. Configuring keys never guaranteed same-source discovery or identity verification.

## Code changes in this review branch

- `app/search_querying.py`: extracts explicit `person called as <full name>` without any hardcoded names; generates up to four diverse queries (original question, name+literal work/organization clue, publisher public-post discovery, education/organization corroboration).
- `app/smart_search.py`: uses that **unverified search label** rather than treating the entire sentence as the person's name and recognizes public cybersecurity/engineering context as a discovery intent.
- `app/v5.py`: four bounded Brave Web Search queries run concurrently (max 3), with original URL candidates stored under case with source and timestamp. Default worldwide country `ALL`.
- `app/retrieval.py`: the chat's person-context selector excludes source records whose only fit is the common name while conflicting with the distinguishing organization/educational clue; the payload retains metrics for excluded namesakes and `identitiesVerified=0`. Normal non-person retrieval remains unchanged.
- `app/main.py`: returns backend-ranked original-source candidate URLs separately from model web leads and conditionally replaces a categorical no-record answer if an overlapping saved public candidate exists, using an explicitly unverified, identity-agnostic assessment.
- `app/analyst.py`: requires the LLM to distinguish an indexed self-reported internship post from independently verified workplace/education credentials.
- `static/console.js`: initiates four targeted Web Search probes, displays `question-filtered candidates (not verified)` instead of misleading `relevant records selected`, and exposes ranked candidate URLs beside the answer. World search is the default.

## Validation and remaining truth limits
- Synthetic 4-query test with publisher-post result, not a real authenticated LinkedIn API call.
- Synthetic 10-name collision test rejects nine irrelevant people and passes only a public indexed work-history lead.
- Synthetic Groq context test ensures unrelated profile snippets are not sent to the model as matching records.
- Synthetic model-hallucination regression refuses a categorical no-record assertion when a matching indexed candidate exists.
- The original public LinkedIn post is **not** an institutional record, evidence of actual employment, education proof or account-ownership verification.
- Real Brave indexing, LLM Context quota, Groq native browser search, LinkedIn page access and source-license terms remain unvalidated from the isolated CI environment; do not report live accuracy scores.
- Search budget is up to four Brave Web Search API requests plus an optional Brave LLM Context request per initial question (in addition to any structured APIs and Groq calls). Provider cost/rate controls still need production validation.

## Manual acceptance path
Open a fresh authorized analyst case and submit a two-attribute name/work/education question. Check **Search coverage** for four executed original and publisher-specific queries; verify at least one matching original public post, and reject unrelated employer biographies as namesakes. In `Search & answer`, inspect the source URLs in the backend-ranked panel. Confirm the education attribute is labeled unverified unless an independent published source supports it. Run cases with no matching source, common names, actual verified source data and a business/tradesperson to ensure no over-filtering.

## Release control
This change is a **stacked review branch**, based on the unmerged P0 first-batch branch. It has not been merged into `main`, and does not validate the remaining 152 tracker issues. No production credentials or case records were accessed.
