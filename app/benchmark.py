"""P0-012: pre-registered head-to-head evaluation, no external service calls.

A test fixture is never a measured comparison against real products.
Two reviewers and source references are minimum *inputs*, not proof of quality.
"""
from __future__ import annotations


class InvalidBenchmark(ValueError):
    pass


def score_trial(trial):
    gold=trial.get('gold') or {}
    expected=set(gold.get('expectedFactIds') or [])
    sources=gold.get('independentSourceUrls') or []
    reviewers=list(gold.get('reviewerIds') or [])
    if not trial.get('question') or not expected or not sources:
        raise InvalidBenchmark('Question, adjudicated fact IDs and reference source URLs required')
    if len(reviewers)<2 or len(set(reviewers))<2:
        raise InvalidBenchmark('Two distinct independent reviewer IDs required')
    outputs=trial.get('outputs') or []
    engines=[x.get('engine') for x in outputs]
    if len(set(engines))<2 or len(outputs)<2:
        raise InvalidBenchmark('Use the identical question for at least two measured engines')
    scored=[]
    for row in outputs:
        if not row.get('evidenceReviewed',False):
            raise InvalidBenchmark('Every engine output requires independent source review')
        supplied=set(row.get('assertedFactIds') or [])
        if not all(isinstance(v,str) and v for v in supplied):
            raise InvalidBenchmark('Claim IDs must be nonblank strings')
        tp=len(supplied & expected)
        scored.append({'engine':row['engine'],
            'truePositiveFactIds':sorted(supplied & expected),
            'unsupportedFactIds':sorted(supplied-expected),
            'precision':round(tp/len(supplied),4) if supplied else None,
            'recall':round(tp/len(expected),4),
            'elapsedMs':row.get('elapsedMs'),
            'costUsd':row.get('costUsd')})
    return {'question':trial['question'],'results':scored,
        'trialScope':'externally_supplied_reviewed_observations',
        'liveResultsCollectedByHarness':False,
        'marketAccuracyEstablished':False,
        'warning':('Input labels must be independently audited. Manual IDs '
                   'cannot prove that the market comparison was actually performed.')}


def score_suite(trials):
    if not trials:
        raise InvalidBenchmark('No independently reviewed trials supplied')
    return {'trials':[score_trial(t) for t in trials],
            'totalTrials':len(trials),'realWorldBenchmarkCertified':False}
