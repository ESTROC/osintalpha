"""P0 012: comparisons require noninvented adjudication inputs."""
import pytest
from app.benchmark import score_trial,InvalidBenchmark


def fixture():
    return {'question':'Find the officially published award date',
        'gold':{'expectedFactIds':['date-2026','organizer-official'],
                'independentSourceUrls':['https://example.org/official-notice'],
                'reviewerIds':['reviewer-1','reviewer-2']},
        'outputs':[
            {'engine':'osintalpha','assertedFactIds':['date-2026'],
             'evidenceReviewed':True,'elapsedMs':350,'costUsd':0.01},
            {'engine':'web_baseline','assertedFactIds':['date-2026','wrong-id'],
             'evidenceReviewed':True,'elapsedMs':450,'costUsd':0.00}]}


def test_012_comparison_preserves_unsupported_claims():
    r=score_trial(fixture())
    assert r['results'][0]['recall']==0.5
    assert r['results'][1]['unsupportedFactIds']==['wrong-id']
    assert r['marketAccuracyEstablished'] is False


def test_012_requires_independent_reviewers():
    sample=fixture()
    sample['gold']['reviewerIds']=['same-person','same-person']
    with pytest.raises(InvalidBenchmark):score_trial(sample)


def test_012_cannot_pretend_mocked_samples_are_real_live_results():
    sample=fixture()
    sample['outputs'][1]['evidenceReviewed']=False
    with pytest.raises(InvalidBenchmark):score_trial(sample)
