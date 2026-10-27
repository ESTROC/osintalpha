"""Honest case-scoped telemetry for later independent live-provider QA (P0-014).

Saved calls and source links are not independent proof that an upstream
provider worked correctly or cited a relevant source.
"""
from collections import Counter


def summarize_provider_evidence(queries, grounding):
    calls=Counter(str(x.get('provider') or 'unknown') for x in queries)
    failures=Counter(str(x.get('provider') or 'unknown') for x in queries
                     if str(x.get('status')) not in {'ok','empty'})
    sources=Counter(str(x.get('provider') or 'unknown') for x in grounding)
    hosts={}
    for row in grounding:
        provider=str(row.get('provider') or 'unknown')
        url=str(row.get('source_url') or '')
        if url.startswith('https://'):
            hosts.setdefault(provider,set()).add(url.split('/')[2].lower())
    return {'providers':[{
        'provider':p,'recordedQueries':calls[p],
        'recordedFailures':failures[p],
        'groundedSourceUrls':sources[p],
        'uniqueHostnameCount':len(hosts.get(p,set())),
        'independentCitationAccuracyVerified':False}
        for p in sorted(set(calls)|set(sources))],
      'liveProviderAcceptancePassed':False,
      'independentGroundTruthReviewed':False,
      'capturedProviderLatencyOrCost':False,
      'requirementsToValidate':[
          'Approved bounded real Brave and Groq test against current staging environment',
          'Exact provider response status, elapsed time, usage and failure conditions',
          'Manual inspection of original publisher pages and citation-to-claim support',
          'Independent reviewer signature and repeatable dated evidence'],
      'notice':('Stored call history or a successful mock is not live-provider '
                'validation, and source URLs do not prove factual claims.')}
