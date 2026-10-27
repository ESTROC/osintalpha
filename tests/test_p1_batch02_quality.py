"""P1 044/046/047: source negatives and publisher-date semantics."""
import pytest
from fastapi import HTTPException
from app.retrieval import rank_case_evidence
from app.date_context import resolve_page_window,date_provenance

def test_044_hard_negative_drops_conflicting_person_clues():
    rows=[
        {'id':'wrong','provider':'github','status':'candidate',
          'label':'Alex engineer','summary':'Alex project',
          'raw_json':'{"location":"Mumbai","company":"DifferentCorp"}'},
        {'id':'right','provider':'github','status':'candidate',
          'label':'Alex engineer','summary':'Alex project',
          'raw_json':'{"location":"Delhi","company":"ExampleOrg"}'},
        {'id':'unknown','provider':'github','status':'candidate',
          'label':'Alex engineer','summary':'Alex project',
          'raw_json':'{}'},
        {'id':'rejected','provider':'github','status':'rejected',
          'label':'Alex engineer','summary':'Alex project','raw_json':'{}'}]
    chosen,info=rank_case_evidence(rows,'Alex engineer',{'city':'Delhi','organization':'ExampleOrg'})
    assert set(r['id'] for r in chosen)=={'right','unknown'}
    assert info['excludedByReason']=={'rejected':1,'conflicting_public_metadata':1}

def test_046_explicit_and_extracted_periods():
    a=resolve_page_window('records between 2019 and 2021')
    assert a['freshness']=='2019-01-01to2021-12-31'
    assert not a['eventDateVerified']
    b=resolve_page_window('2025 case',date_from='2020-02-01',date_to='2020-03-31')
    assert b['derivedFrom']=='explicit_fields'
    assert resolve_page_window('public awards in 2024')['intervalFrom']=='2024-01-01'

@pytest.mark.parametrize('start,end',[
    ('2024-02-30','2024-03-01'),('2025-01-01','2024-01-01')])
def test_046_invalid_ranges_fail(start,end):
    with pytest.raises(HTTPException):resolve_page_window('topic',start,end)

def test_047_provenance_does_not_invent_event_date():
    r=date_provenance({'page_age':'2 years ago','page_fetched':'2026-10-20T00:00:00Z'},
                      '2026-10-28T00:00:00Z')
    assert r['publisherEventDate'] is None
    assert r['publisherPublicationDate'] is None
    assert r['systemRetrievedAt']=='2026-10-28T00:00:00Z'
