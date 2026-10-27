"""Case-scoped provider and evidence outcome completeness.

Never translate no search hits, an API failure, or a rejected lead into proof
that a person, organization, or fact does not exist.
"""
from __future__ import annotations
from collections import Counter


def summarize(runs, evidence=(), expected=()):
    """Most recent attempt per provider, plus explicitly unsearched providers.

    Each run must contain provider/state/ran_at. Older successes never erase
    the latest error; scope is the supplied cases' authorized observations.
    """
    latest = {}
    for row in sorted(runs, key=lambda r: str(r.get('ran_at') or ''), reverse=True):
        provider = str(row.get('provider') or '').strip()
        if provider and provider not in latest:
            latest[provider] = row
    providers = []
    for name in dict.fromkeys([*expected, *latest]):
        if not isinstance(name, str) or not name.strip():
            continue
        row = latest.get(name)
        state = str(row.get('state') or '').lower() if row else 'not_searched'
        if state not in {'ok', 'empty', 'error', 'blocked', 'unsupported',
                         'not_configured', 'unavailable'}:
            state = 'unknown'
        providers.append({
            'provider': name, 'state': state,
            'attempted': row is not None,
            'returnedCount': int(row.get('result_count') or 0) if row else 0,
            'ranAt': str(row.get('ran_at') or '') if row else '',
            'message': str(row.get('message') or '')[:250] if row else
                       'No recorded attempt for this case.',
        })
    state_counts = dict(Counter(item['state'] for item in providers))
    findings = dict(Counter(str(x.get('status') or 'unknown') for x in evidence))
    found = sum(findings.get(k, 0) for k in ('candidate', 'corroborated', 'disputed'))
    failed = sum(state_counts.get(k, 0) for k in
                 ('error', 'blocked', 'unsupported', 'not_configured', 'unavailable', 'unknown'))
    unsearched = state_counts.get('not_searched', 0)
    if found:
        outcome = 'unverified_candidates_found'
    elif failed:
        outcome = 'incomplete_provider_failures'
    elif unsearched or not providers:
        outcome = 'incomplete_not_searched'
    elif state_counts.get('empty') and not state_counts.get('ok'):
        outcome = 'no_hits_in_attempted_sources'
    else:
        outcome = 'no_saved_relevant_evidence'
    return {
        'outcome': outcome,
        'providerStates': providers,
        'providerCounts': state_counts,
        'evidenceStates': findings,
        'candidateCount': found,
        'analystRejectedCount': findings.get('rejected', 0),
        'unsearchedProviderCount': unsearched,
        'failedProviderCount': failed,
        'canConcludeSubjectOrClaimAbsent': False,
        'identityVerified': False,
        'limitation': (
            'No hits are not proof of absence. An API failure is not a no-hit result. '
            'Rejected evidence is an analyst judgement, not proof of mistaken identity. '
            'Source records and analyst corroboration are not independent identity verification.'
        ),
    }
