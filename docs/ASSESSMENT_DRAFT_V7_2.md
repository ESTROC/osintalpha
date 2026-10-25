# OSINT Alpha V7.2 — Grounded analyst assessment drafts

- New POST /api/cases/{case_id}/assessment-draft, with local (deterministic source-ledger) and optional groq model-assisted drafting.
- Drafts require at least one current, exact-match quotation from a source text capture in the same case. Rejected or changed captures are excluded.
- Local mode assembles directly attributable source URL + verbatim quotation + analyst interpretation, and clearly states that identity and source claims are unverified.
- Groq mode requires explicit case-level remote AI consent and a configured GROQ_API_KEY. The model proposes a structured interpretation and referenced passage IDs; original matching source passages are attached to the returned analysis for review.
- No draft automatically changes the saved case assessment, case status, or evidence classification. The analyst must review and click Save assessment.
- The UI warns before replacing unsaved form text; errors do not silently substitute fabricated citations.
- Six mocked provider/security/integrity tests cover absent, rejected, outdated and case-inaccessible source captures, consent boundaries and manual-save behavior.

## Important limits
Text matching is not independent factual verification, source authenticity or identity attribution. The model can still draw invalid inferences from source content; every material assertion requires analyst checking and independent corroboration. Full automatic entailment testing, broad-web recall, calibrated identity linking, enterprise SSO/MFA and production-grade recovery remain undelivered.

## Backend configuration
The built-in ledger needs no external AI. Optional model-assisted drafting uses the private backend GROQ_API_KEY and the existing explicit case AI opt-in. Do not commit secrets or assume provider availability from synthetic CI tests.
