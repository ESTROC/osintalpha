"""P2 131–133: review tasks, isolated feedback and scope-preserving checklist."""
def test_new_claim_creates_unique_owner_review_task(client,auth,case):
    e=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
       'label':'Review candidate','summary':'A source to review',
       'source_url':'https://example.org/report'})
    assert e.status_code==200,e.text
    c=client.post(f'/api/cases/{case}/claims',headers=auth,json={
       'evidence_id':e.json()['id'],'claim_text':'A synthetic source claims a public finding','stance':'supports'})
    assert c.status_code==201,c.text
    queue=client.get(f'/api/cases/{case}/review-obligations')
    assert queue.status_code==200 and len(queue.json()['items'])==1
    item=queue.json()['items'][0]
    assert item['trigger_kind']=='uncited_claim'
    assert item['status']=='awaiting_review'
    from app.analyst_governance import queue as enqueue
    from app import db
    with db.connect() as conn:
        case_owner=conn.execute('SELECT created_by FROM cases WHERE id=?',(case,)).fetchone()['created_by']
        same,added=enqueue(conn,case,case_owner,'uncited_claim',c.json()['id'],'Duplicate','Duplicate')
    assert not added and same==item['task_id']
    finished=client.patch(f'/api/cases/{case}/tasks/{item["task_id"]}',headers=auth,json={
        'status':'done','note':'Reviewer examined the original source but the claim remains unsupported.'})
    assert finished.status_code==200,finished.text

def test_template_does_not_change_authorization_and_feedback_baseline(client,auth,case):
    catalog=client.get('/api/research/investigation-templates')
    assert catalog.status_code==200
    bad=client.post(f'/api/cases/{case}/investigation-template',headers=auth,
       json={'template_id':'defensive_domain'})
    assert bad.status_code==422
    report=client.get(f'/api/cases/{case}/feedback-quality-baseline')
    assert report.status_code==200
    assert report.json()['trainingPerformed'] is False
    assert report.json()['precisionLiftMeasured'] is None
