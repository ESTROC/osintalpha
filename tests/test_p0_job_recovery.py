"""P0-024: durable job cancellation, failure state and explicit recovery."""
from app import agent

def test_024_ready_job_cancelled_and_not_restarted(client,auth,case):
    jid=client.post(f'/api/cases/{case}/jobs',headers=auth,json={
        'objective':'Review bounded published professional activity'}).json()['id']
    resp=client.post(f'/api/cases/{case}/jobs/{jid}/cancel',headers=auth)
    assert resp.status_code==200,resp.text
    assert resp.json()['status']=='cancelled'
    assert client.post(f'/api/cases/{case}/jobs/{jid}/step',headers=auth).status_code==409
    assert client.post(f'/api/cases/{case}/jobs/{jid}/recover',headers=auth).status_code==409


def test_024_provider_error_requires_recovery(client,auth,case,monkeypatch):
    jid=client.post(f'/api/cases/{case}/jobs',headers=auth,json={
        'objective':'Review bounded published professional activity',
        'max_steps':3}).json()['id']
    async def provider_failure(case,job,choice,actor_id,step_no):
        return {'status':'error','returned':0,'new':0,'changed':0,
                'message':'synthetic quota exhaustion'}
    monkeypatch.setattr(agent,'execute_provider',provider_failure)
    r=client.post(f'/api/cases/{case}/jobs/{jid}/step',headers=auth)
    assert r.status_code==200,r.text
    assert r.json()['status']=='failed'
    assert r.json()['completedSteps']==1
    assert client.post(f'/api/cases/{case}/jobs/{jid}/step',headers=auth).status_code==409
    recovered=client.post(f'/api/cases/{case}/jobs/{jid}/recover',headers=auth)
    assert recovered.status_code==200
    assert recovered.json()['status']=='ready'
    assert recovered.json()['completedSteps']==1


def test_024_cooperative_cancel_requested_is_preserved(client,auth,case,monkeypatch):
    jid=client.post(f'/api/cases/{case}/jobs',headers=auth,json={
        'objective':'Review bounded published professional activity'}).json()['id']
    from app import db
    with db.connect() as conn:
        conn.execute("UPDATE research_jobs SET status='running' WHERE id=?",(jid,))
    r=client.post(f'/api/cases/{case}/jobs/{jid}/cancel',headers=auth)
    assert r.status_code==200
    assert r.json()['status']=='cancel_requested'
