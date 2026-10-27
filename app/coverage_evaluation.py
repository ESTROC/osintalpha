"""P0-027: transparent case coverage and reference recall@k evaluator.

A self-supplied gold list is NOT independently validated; this module cannot
prove universal public-web recall or calibrated real-world quality.
"""
from urllib.parse import urlsplit
from collections import Counter


def case_coverage(evidence,queries,limit=35):
    from .search_policy import publisher_group
    unique={str(x.get('source_url') or '') for x in evidence if x.get('source_url')}
    hosts={publisher_group(url) for url in unique if urlsplit(url).scheme=='https'}
    selected=evidence[:limit]
    truncated=max(0,len(evidence)-len(selected))
    states=Counter(str(x.get('status') or 'candidate') for x in evidence)
    return {'storedRecordCount':len(evidence),'uniqueSourceUrlCount':len(unique),
        'uniquePublisherGroups':len(hosts),'rankedContextWindow':limit,
        'recordsExcludedFromContextWindow':truncated,
        'sourceStatusCounts':dict(states),
        'queryAttemptsRecorded':len(queries),
        'measuredRecallAtK':None,
        'questionCoverageIndependentlyVerified':False,
        'limitation':('Host diversity and stored results are not a recall benchmark. '
          'Duplicate domains do not prove independent corroboration.')}


def reference_recall_at_k(ranked_source_urls,reference_urls,k=10,reviewer_ids=()):
    if k<1 or k>100:raise ValueError('k must be between 1 and 100')
    gold={str(u).strip() for u in reference_urls if str(u).startswith('https://')}
    if not gold:raise ValueError('Nonempty source-referenced gold set required')
    if len(set(reviewer_ids))<2:raise ValueError('Two separate reviewer IDs required')
    ranked=list(dict.fromkeys(str(u) for u in ranked_source_urls if str(u).startswith('https://')))
    selected=ranked[:k]
    matching=set(selected)&gold
    return {'k':k,'referenceUrls':len(gold),'retrievedUrls':len(selected),
            'correctSourceUrls':len(matching),
            'recallAtK':round(len(matching)/len(gold),4),
            'precisionAtK':round(len(matching)/len(selected),4) if selected else None,
            'independentTruthSetVerifiedBySystem':False,
            'limitation':'Reviewer IDs and self-supplied URLs are not proof of adjudication.'}
