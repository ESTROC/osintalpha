"""P0-021/028: no remote private-person targeting or AI allegation publication."""
import pytest
from fastapi import HTTPException
from app.research_safety import (classify_remote_query,require_safe_remote_query,
                                 guard_high_risk_claim)

@pytest.mark.parametrize('query',[
  'Find the residential address of Jane Doe',
  'Get private mobile number of Jane Doe',
  'Track this person to find their current location',
  'What is Jane Doe passport number',
  'Infer her religion from public profile'])
def test_028_person_private_queries_blocked(query):
    assert not classify_remote_query(query,'person')['allowed']
    with pytest.raises(HTTPException) as error:
        require_safe_remote_query(query,'person')
    assert error.value.status_code==422

def test_028_public_employment_research_still_allowed():
    assert require_safe_remote_query('Find published projects of Alex Shah at a university')['allowed']

def test_028_organization_queries_not_misclassified_as_person_queries():
    assert classify_remote_query('public registered office address','organization')['allowed']

def test_021_allegation_suppressed_not_reframed_as_verified():
    result=guard_high_risk_claim('Alex Shah committed fraud.','Who is Alex?','person')
    assert result['action']=='withhold_unreviewed_serious_allegation'
    assert 'committed fraud' not in result['answer']
    assert not result['automaticallyApproved']

def test_021_non_person_or_non_allegation_result_not_rewritten():
    assert guard_high_risk_claim('The published event is on Friday','event','person')['action']=='no_high_risk_claim_detected'
    assert guard_high_risk_claim('A public corporation reports fraud allegations','report','organization')['action']=='no_high_risk_claim_detected'
