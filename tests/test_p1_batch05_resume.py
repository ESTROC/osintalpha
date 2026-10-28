"""P1 077/078: saved question and staged plan resume without duplicate job billing."""
from app.resumable_search import derive_progress

def test_078_question_and_provider_state_not_inferred_from_no_hits():
    r=derive_progress('Who organized a public festival?',{'providers':['wikipedia','gdelt']},
        [{'provider':'wikipedia','status':'empty','returned_count':0}],[])
    assert r['originalQuestion']=='Who organized a public festival?'
    assert r['plannedStructuredSources'][0]['status']=='no_hits'
    assert r['plannedStructuredSources'][1]['status']=='not_searched'
    assert not r['researchCompletenessVerified']

def test_077_saved_search_can_create_single_resumable_job(client,auth):
    created=client.post('/api/search/start',headers=auth,json={
        'question':'Public professional projects by Example Person in 2024',
        'purpose':'Authorized synthetic public-source project review',
        'authority_confirmed':True,'ai_opt_in':False,'subject_type':'person'})
    assert created.status_code==201,created.text
    cid=created.json()['id']
    first=client.get(f'/api/cases/{cid}/search-progress')
    assert first.status_code==200
    assert first.json()['available']
    assert 'Example Person' in first.json()['originalQuestion']
    one=client.post(f'/api/cases/{cid}/resume-saved-research',headers=auth)
    two=client.post(f'/api/cases/{cid}/resume-saved-research',headers=auth)
    assert one.status_code==201,one.text
    assert two.status_code==201,two.text
    assert one.json()['jobId']==two.json()['jobId']
    assert two.json()['reusedExisting']
    assert one.json()['requiresExplicitSteps']
    assert client.get(f'/api/cases/{cid}/search-plan').json()['available']
