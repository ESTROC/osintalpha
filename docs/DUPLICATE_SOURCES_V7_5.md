# V7.5 — Public-source duplicate review

## What is implemented
- A case-scoped duplicate-source detector using conservative canonical URLs, DOI identifiers and cross-provider highly similar publication titles.
- Exact URLs/DOIs are labeled as potential duplicate source records, not independent corroboration.
- A shared person name does not trigger a source merge; near-duplicate titles are human-review suggestions, not verified shared identities.
- The evidence workbench presents original record pairs for direct inspection. No records, identities, statuses or source links are automatically merged or destroyed.
- Tests cover DOI records across providers, canonical URL query parameters, namesakes, title similarity and cross-case access isolation.

## Limits
This does not perform comprehensive internet-wide deduplication, forensic source identity verification, independent claim corroboration or automatic verified person disambiguation. The detector works on at most 750 saved case records per call. Its URL normalizer may group web and www versions that are distinct on rare websites; every suggestion is subject to review.
