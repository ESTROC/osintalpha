"""Independent-judgment identity evaluation harness — NO implicit truth claims.

Gold labels must come from a consented and independently adjudicated dataset.
Analyst-reviewed candidate labels alone are not ground truth. This module
reports coverage, signal false alerts and abstention; it does not validate a
provider unless the reference set was manually accepted.
"""
from __future__ import annotations
from collections import Counter
import json

def score_reference_set(entries, *, minimum=20):
    if not isinstance(entries,list):
        raise ValueError('Gold reference must be a list')
    if len(entries)<minimum:
        raise ValueError('Independent benchmark needs at least '+str(minimum)+' reference pairs')
    references=set()
    stats=Counter()
    for row in entries:
        if not isinstance(row,dict):
            raise ValueError('Malformed benchmark row')
        rid=str(row.get('pair_id') or '')
        truth=row.get('adjudicated_same_person')
        signal=row.get('source_signal')
        source=str(row.get('adjudication_reference') or '')
        reviewers=row.get('independent_reviewer_ids') or []
        if not rid or rid in references or not isinstance(truth,bool):
            raise ValueError('Unique ID and independently established true/false required')
        if signal not in ('candidate_link','abstain'):
            raise ValueError('Only candidate-link signal or abstention allowed')
        if not source or not isinstance(reviewers,list) or len(set(reviewers))<2:
            raise ValueError('Each truth label needs a source and two independent reviewers')
        references.add(rid)
        stats['positive' if truth else 'negative']+=1
        stats['signal' if signal=='candidate_link' else 'abstain']+=1
        stats['false_link_signal' if signal=='candidate_link' and not truth else 'other']+=1
        stats['missed_link_signal' if signal=='abstain' and truth else 'other']+=1
    if stats['positive']<5 or stats['negative']<5:
        raise ValueError('Include both confirmed-positive and negative namesakes')
    def frac(a,b):
        return round(a/b,4) if b else None
    return {
        'totalPairs':len(entries),'positivePairs':stats['positive'],
        'negativeNamesakePairs':stats['negative'],
        'candidateLinkSignals':stats['signal'],
        'abstentions':stats['abstain'],
        'falseLinkSignals':stats['false_link_signal'],
        'falseLinkRateOnNegatives':frac(stats['false_link_signal'],stats['negative']),
        'missedLinkSignals':stats['missed_link_signal'],
        'abstentionRate':frac(stats['abstain'],len(entries)),
        'interpretation':'Candidate-link signals are NOT automatic same-person attributions.',
        'groundTruthStatus':'reviewer_supplied_not_independently_audited_by_software'
    }

def score_json(path):
    with open(path,'r',encoding='utf-8') as f:
        rows=[json.loads(line) for line in f if line.strip()]
    return score_reference_set(rows)

if __name__=='__main__':
    import sys
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python -m app.identity_benchmark approved_gold.jsonl')
    print(json.dumps(score_json(sys.argv[1]),indent=2))
