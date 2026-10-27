# V7.8 — Question-led public-source research and Groq + Brave context

## Who the investigation is for

OSINT Alpha must not assume that the subject has academic publications, a LinkedIn account, a CV or a GitHub portfolio. A student, tradesperson, informal worker, company, public institution or individual with a sparse online presence may require entirely different public records, or may have no reliable web presence.

Research lenses: general public information, trade/local services, education/public activities, and professional profiles. These are search-plan starting points, **not identity classifications**. Brave results about a name are leads, not automatically records about the intended person.

## Live Brave context for Groq

The analyst can explicitly select "Retrieve fresh, attributed Brave context" in case-scoped Groq chat when both `GROQ_API_KEY` and `BRAVE_SEARCH_API_KEY` are configured privately. It requires the existing remote-AI case consent.

On each selected question, a single limited call to the Brave LLM Context API retrieves up to seven HTTPS sources with extracted snippets and available publisher/index dates, and passes the limited snippets to Groq as **untrusted source claims** alongside saved case evidence. The assistant includes original-source URLs that the backend validates against returned sources; unrecognized model-generated Markdown URLs are removed.

The returned sources are exposed as *reviewable public leads*. Neither the complete page contents nor any inferred identity is automatically saved/confirmed. The analyst can manually inspect and save appropriate leads. Factual truth, original authorship, publisher independence and identity match are not guaranteed by Brave or Groq.

Groq's own browser search remains a separate mode; it cannot be selected simultaneously with this Brave context call. Network failures, missing keys or quotas produce explicit errors instead of invented findings. A request cap helps meet the Vercel proxy timeout.

## Release gates still outstanding

Independently verified sources and name-collision benchmarks, controlled false-positive and abstention measurements, claim entailment, authenticated browser E2E, privacy/security assessment, checked source storage rights and tested PostgreSQL backups. The old 12/95 audit is not a current V7.8 completion result.

Geographic observation and public-camera functionality are **unchanged** in this release. No location tracking or surveillance workflow is connected to people investigations.
