"""P0 013: auditable administrator research scope and retention policy."""
from app import db


def test_013_requires_non_generic_scope_and_explicit_approval(client,auth,case):
    payload={'specific_scope':'Review published activities of a single identified graduate',
        'authorization_category':'internal_public_research',
        'approval_reference':'INTERNAL-TEST-2026','retention_days':30}
    assert client.post(f'/api/cases/{case}/authorization',headers=auth,
        json=payload).status_code==422
    payload['approve']=True
    assert client.post(f'/api/cases/{case}/authorization',headers=auth,
        json=payload).status_code==200
    result=client.get(f'/api/cases/{case}/authorization')
    assert result.status_code==200
    assert result.json()['recordedApproval']['retention_days']==30
    assert result.json()['independentLegalAuthorizationVerified'] is False


def test_013_optional_gate_prevents_remote_collection_without_approval(
        client,auth,case,monkeypatch):
    monkeypatch.setenv('OSINTALPHA_ENFORCE_CASE_SCOPE','1')
    result=client.post(f'/api/cases/{case}/web-discovery',
        headers=auth,json={'consent':True})
    assert result.status_code==403
    assert 'administrator-reviewed' in result.json()['detail']
    monkeypatch.delenv('OSINTALPHA_ENFORCE_CASE_SCOPE')


def test_013_case_approval_is_scoped_not_reused(client,auth,case):
    other=client.post('/api/cases',headers=auth,json={
        'title':'Other research case','subject_type':'person','query':'Other Person',
        'purpose':'Public professional background comparison',
        'authority_confirmed':True}).json()['id']
    assert client.get(f'/api/cases/{other}/authorization').json()['recordedApproval'] is None
    assert client.get('/api/cases/not-here/authorization').status_code==404
