"""P0 027: coverage measured only against explicit gold sources."""
import pytest
from app.coverage_evaluation import reference_recall_at_k,case_coverage


def test_027_reference_recall_counts_missing_sources():
    gold=['https://example.org/a','https://example.org/b','https://example.org/c']
    r=reference_recall_at_k(
        ['https://example.org/a','https://example.org/x'],gold,k=2,
        reviewer_ids=['reviewer-A','reviewer-B'])
    assert r['recallAtK']==0.3333
    assert r['precisionAtK']==0.5
    assert r['independentTruthSetVerifiedBySystem'] is False


def test_027_rejects_unreviewed_or_empty_reference():
    with pytest.raises(ValueError):
        reference_recall_at_k(['https://example.org/x'],[],reviewer_ids=['a','b'])
    with pytest.raises(ValueError):
        reference_recall_at_k(['https://example.org/x'],['https://example.org/x'],
                              reviewer_ids=['same','same'])


def test_027_case_summary_not_misrepresented_as_recall(client,auth,case):
    response=client.get(f'/api/cases/{case}/coverage-index')
    assert response.status_code==200,response.text
    assert response.json()['measuredRecallAtK'] is None
    assert response.json()['questionCoverageIndependentlyVerified'] is False
    assert client.get('/api/cases/forbidden/coverage-index').status_code==404


def test_027_truncation_does_not_claim_exhaustiveness():
    rows=[{'source_url':f'https://example.org/{i}','status':'candidate'}
          for i in range(40)]
    r=case_coverage(rows,[],limit=35)
    assert r['recordsExcludedFromContextWindow']==5
    assert r['uniquePublisherGroups']>=1
    assert r['measuredRecallAtK'] is None
