"""P1-045/048: audit-oriented routing and explicit official no-hit checks."""
from app.query_diagnostics import explain_queries,official_url

def test_045_explain_planned_does_not_claim_executed():
    r=explain_queries({'providers':['github'],'queryVariants':['Anna Gupta','"Anna Gupta" engineer']},
        [{'provider':'github','query_text':'Anna Gupta','status':'error','returned_count':0,'created_at':'2026-10-28'}])
    assert r['plannedQueryVariants'][0]['executed']
    assert not r['plannedQueryVariants'][1]['executed']
    assert r['executedQueries'][0]['status']=='error'
    assert not r['executedQueries'][0]['isProofOfAbsence']

def test_048_public_official_source_only():
    assert official_url('https://www.mcacdm.nic.in/company-master-details')
    assert not official_url('https://mca.gov.in.attacker.invalid/x')
    assert not official_url('http://services.gst.gov.in')
    assert not official_url('https://example.com/page')

def test_048_manual_nonmatch_requires_case_and_attribution(client,auth,case):
    payload={'query':'Example Registered LLP','source_url':'https://www.mcacdm.nic.in/company-master-details',
             'search_scope':'Company master details on a selected date',
             'limitation':'The public page might not list all historic records'}
    assert client.post(f'/api/cases/{case}/official-nonmatch',headers=auth,json=payload).status_code==422
    payload['confirm_reviewed']=True
    resp=client.post(f'/api/cases/{case}/official-nonmatch',headers=auth,json=payload)
    assert resp.status_code==201,resp.text
    assert not resp.json()['provesAbsence']
    read=client.get(f'/api/cases/{case}/official-nonmatches')
    assert read.status_code==200
    assert read.json()['items'][0]['sourceUrl']==payload['source_url']
    assert not read.json()['noMatchIsProofOfNonexistence']
    assert client.get('/api/cases/no-case/query-explain').status_code==404
