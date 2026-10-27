# V7.8 — General-purpose public research, live Brave context and publisher cameras

## Scope and intended analyst workflow

The investigator chooses a legitimate case purpose and a research question. A person need not be employed, formally educated, a researcher, a developer, or even discoverable on the internet.

### Broad discovery

The Portfolio tab now lets an analyst choose general public information, trades/local services, education/public activities, or professional profile leads. The API supports the same `lens` parameter at `POST /api/cases/{id}/web-discovery`. All results remain **unverified source leads**. LinkedIn public search result URLs are not logged-in LinkedIn records.

Generic public-web leads are listed as `public_web_lead`, not falsely presented as a person's profile. The source's relationship to the subject must be established separately.

### Brave-to-Groq grounded answers

The case assistant adds "Retrieve fresh, attributed Brave context for this question" for consent-enabled Groq sessions when `BRAVE_SEARCH_API_KEY` exists. Requires both `GROQ_API_KEY` and `BRAVE_SEARCH_API_KEY` only on the private backend.

- Request `POST /api/cases/{id}/chat` with `provider=groq`, `brave_context=true` and a real question.
- A single constrained Brave LLM Context request retrieves up to seven relevant HTTPS original-source URLs plus bounded excerpts and available dates.
- The Groq prompt receives those excerpts explicitly marked as unverified third-party input, in addition to case-owned saved evidence.
- The response exposes the original Brave URLs under `webLeads` for analyst review and optional saved evidence; model-generated Markdown links outside the actual retrieved source set are removed.
- The full third-party page content is **not** automatically stored in the evidence database. A saved web lead is not evidence of real-world identity or truth.
- `brave_context` and Groq-hosted `web_search` are mutually exclusive in one question. External model consent remains required. If Brave is empty or down, no fake fallback facts are generated.
- No arbitrary network crawl, private account browsing, profile scraping, residential-address search or live person tracking.
- Bounded request timeouts protect the Vercel same-origin proxy. Costs depend on actual Brave/Groq quota.

### Geographic source catalog / cameras

TfL's official JamCam directory can be requested without an API key under TfL's limited anonymous rate tier. A configured key can raise rate limits. Where the publisher marks a camera available and the image URL passes a strict official TfL S3 allowlist, an analyst can click **View official still** from the separate World Intelligence / London traffic layer. Images are loaded only on request, labeled **Powered by TfL Open Data**, and are explicitly not verified to be current. Source metadata does not provide confirmed per-frame capture timestamps, even if individual original images have a visible time stamp.

Caltrans uses its own official QuickMap publisher link and metadata; no unsupported frame relay is claimed. World event layers remain separate from any person case, and there is **no linking of personal whereabouts to cameras or live location predictions**.

## Remains unproven/open

- Live Brave credentials/quota/provider output (synthetic integration tests do not prove internet coverage or identity match quality)
- External publication/site author identity and original-source authenticity
- Broad identity adjudication benchmark with verified negative namesakes
- Claim-to-passage entailment, source independence analysis and agent citation verification
- Licensed real camera feed timestamps and broad regional feeds beyond the official publishers
- Playwright browser acceptance, durability/backup, security assessment and commercial rights review
- Original 95-item numbered audit against real acceptance checks

Do not claim V7.8 is 95/95 or an enterprise-certified intelligence system.
