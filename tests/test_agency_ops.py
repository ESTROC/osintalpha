"""Agency toolkit: permissions, provenance, pagination and review outcomes."""
from app import db


def test_aliases_and_source_taxonomy(client,auth,case):
    p='/api/cases/'+case+'/aliases'
    req={'alias':'Example Name','alias_type':'alternative_name',
         'source_url':'https://example.org/record','rationale':'Recorded by analyst for public research'}
    assert client.post(p,json=req).status_code==403
    assert client.post(p,headers=auth,json=req).status_code==201
    assert client.post(p,headers=auth,json=req).status_code==409
    assert client.post(p,headers=auth,json={**req,'source_url':'http://127.0.0.1'}).status_code==422
    results=client.get(p).json()['items']
    assert len(results)==1 and results[0]['alias_type']=='alternative_name'
    providers=client.get('/api/source-taxonomy').json()['sources']
    assert any(p['id']=='github' and 'technical' in p['coverage'] for p in providers)


def test_evidence_pagination_timeline_and_methods(client,auth,case):
    for i in range(4):
        r=client.post('/api/cases/'+case+'/evidence',headers=auth,json={
            'label':'Public sample '+str(i),
            'summary':'A synthetic public reference not yet verified',
            'source_url':'https://example.org/sample/'+str(i)})
        assert r.status_code==200
    paged=client.get('/api/cases/'+case+'/evidence-page?limit=2&offset=0').json()
    assert paged['total']==4 and len(paged['items'])==2 and paged['hasMore']
    second=client.get('/api/cases/'+case+'/evidence-page?limit=2&offset=2').json()
    assert len(second['items'])==2 and not second['hasMore']
    timeline=client.get('/api/cases/'+case+'/timeline').json()['items']
    assert len(timeline)==4 and all(x['dateBasis']=='retrieved_only' for x in timeline)
    method=client.get('/api/cases/'+case+'/methodology').json()
    assert 'unqueriedStructuredSources' in method
    assert method['scope']=='Authorized professional qualifications research'


def test_relationship_requires_original_case_evidence(client,auth,case):
    p='/api/cases/'+case+'/relationships'
    b={'left_name':'Example Firm','right_name':'Example Service',
       'relationship':'public affiliation',
       'evidence_id':'not-in-case-123',
       'rationale':'A direct public claim in an original document'}
    assert client.post(p,headers=auth,json=b).status_code==404
    evidence=client.post('/api/cases/'+case+'/evidence',headers=auth,json={
        'label':'Public affiliation listing','summary':'An unverified association in a public page',
        'source_url':'https://example.org/affiliation'}).json()['id']
    out=client.post(p,headers=auth,json={**b,'evidence_id':evidence})
    assert out.status_code==201
    rid=out.json()['id']
    assert client.get(p).json()['items'][0]['review_state']=='proposed'
    r=client.patch(p+'/'+rid,headers=auth,json={
       'review_state':'reviewed_public_record',
       'note':'Reviewer checked only the presence of this publisher assertion'})
    assert r.status_code==200
    assert r.json()['reviewState']=='reviewed_public_record'


def test_evidence_pack_reviewer_gate_and_signoff_staleness(client,auth,case):
    link='/api/cases/'+case+'/evidence'
    ev=client.post(link,headers=auth,json={
        'label':'A public claim candidate','summary':'Claim in an attributed test page',
        'source_url':'https://example.org/claim'}).json()['id']
    pack=client.get('/api/cases/'+case+'/evidence-pack').json()
    assert pack['evidence']==[] and pack['claims']==[]
    raw=client.get('/api/cases/'+case+'/evidence-pack?reviewed_only=false').json()
    assert len(raw['evidence'])==1 and not raw['signoffCurrent']
    assert client.post('/api/cases/'+case+'/signoffs',headers=auth,json={
        'decision':'reviewed_with_limitations',
        'note':'The record was inspected but no finalized assessment exists.'}).status_code==422
    no=client.post('/api/cases/'+case+'/signoffs',headers=auth,json={
        'decision':'not_approved','note':'Insufficient verified source evidence for client release.'})
    assert no.status_code==201
    assert client.get('/api/cases/'+case+'/signoffs').json()['items'][0]['stillCurrent']
    client.patch('/api/evidence/'+ev,headers=auth,json={'status':'disputed','reviewer_notes':'Possible unrelated namesake'})
    assert not client.get('/api/cases/'+case+'/signoffs').json()['items'][0]['stillCurrent']


def test_recipe_and_access_control(client,auth,case):
    p='/api/research/recipes'
    assert client.get(p).status_code==200
    assert any(x['id']=='student' for x in client.get(p).json()['builtIn'])
    created=client.post(p,headers=auth,json={'title':'Trade inquiry',
        'description':'Public service presence','question':'Find public service listing and official business registry'})
    assert created.status_code==201
    assert created.json()['version']==1
    assert len(client.get(p).json()['saved'])==1
    assert client.get('/api/cases/'+case+'/source-feedback').status_code in (404,405)
    assert client.get('/api/agency/compare-cases?left='+case+'&right='+case).status_code==422
    assert client.get('/api/cases/not-accessible/methodology').status_code==404


def test_feedback_and_translation_are_analyst_assertions(client,auth,case):
    ev=client.post('/api/cases/'+case+'/evidence',headers=auth,json={
        'label':'Public foreign text','summary':'Original foreign-language publicly supplied excerpt',
        'source_url':'https://example.org/international'}).json()['id']
    r=client.post('/api/cases/'+case+'/source-feedback',headers=auth,json={
        'evidence_id':ev,'relevance':'wrong_subject',
        'rationale':'This record refers to a different named candidate'})
    assert r.status_code==201
    assert r.json()['trainingStatus']=='feedback_recorded_not_automatically_trained'
    t=client.post('/api/cases/'+case+'/translation-notes',headers=auth,json={
        'evidence_id':ev,'language':'Hindi','source_quote':'A synthetic phrase from a public notice',
        'translation':'A synthetic English translation for analyst review',
        'translator':'Human analyst'})
    assert t.status_code==201
    assert 'not machine OCR' in t.json()['notice']
    assert len(client.get('/api/cases/'+case+'/translation-notes').json()['items'])==1


def test_metrics_status_and_no_false_independence(client,auth,case):
    assert client.get('/api/agency/metrics').status_code==200
    assert client.get('/api/research/ops-status').json()['apiStatus']=='ok'
    assert client.get('/api/cases/'+case+'/citation-overlap').json()['repeatedWebCitations']==[]


def test_answer_diff_denies_cross_case_access(client,auth,case):
    assert client.get('/api/cases/'+case+'/answer-diff?left=x&right=y').status_code==404


def test_review_tasks_batch_and_redacted_export(client,auth,case):
    e=client.post('/api/cases/'+case+'/evidence',headers=auth,json={
        'label':'A public lead about two namesakes','summary':'Review original record and potential namesakes',
        'source_url':'https://example.org/name'}).json()['id']
    p='/api/cases/'+case
    suggested=client.post(p+'/suggest-review-tasks?limit=2',headers=auth)
    assert suggested.status_code==200 and suggested.json()['created']==1
    assert client.post(p+'/suggest-review-tasks',headers=auth).json()['created']==0
    task=suggested.json()['taskIds'][0]
    # Bulk verification/completion must be impossible.
    assert client.post(p+'/tasks/batch',headers=auth,json={
        'ids':[task],'status':'done','note':'Should not complete with a batch operation'}).status_code==422
    updated=client.post(p+'/tasks/batch',headers=auth,json={
        'ids':[task],'status':'awaiting_review',
        'note':'This candidate needs exact-source attribution before closure.'})
    assert updated.status_code==200 and updated.json()['changed']==1
    preview=client.get(p+'/export-preview?reviewed_only=false&redact_labels=true').json()
    assert preview['counts']['included']==1
    assert preview['preview'][0]['label']=='[redacted candidate label]'
    assert preview['preview'][0]['url'] is None
    assert preview['signedOff'] is False


def test_case_to_case_comparison_requires_both_permissions(client,auth,case):
    second=client.post('/api/cases',headers=auth,json={
        'title':'Separate authorized study','subject_type':'person','query':'Second Candidate',
        'purpose':'Synthetic related-source overlap validation','authority_confirmed':True}).json()['id']
    path='/api/agency/compare-cases?left='+case+'&right='+second
    data=client.get(path).json()
    assert data['commonSources']==0 and data['left']['records']==0
    assert client.get('/api/agency/compare-cases?left='+case+'&right=not-a-case').status_code==404


def test_public_cam_freshness_whitelist_and_canary_requires_optin(client,auth,monkeypatch):
    from app.connectors import public_tfl_still
    url='https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.07450.jpg'
    assert public_tfl_still(url)==url
    assert public_tfl_still('https://example.org/img.jpg')==''
    assert client.post('/api/research/provider-canary',headers=auth,json={
        'provider':'github','consent':False}).status_code==422
    assert client.post('/api/research/provider-canary',headers=auth,json={
        'provider':'not-real','consent':True}).status_code==422
    from app import connectors
    async def fake_collect(provider,query,kind):
        return []
    monkeypatch.setattr(connectors,'collect_one',fake_collect)
    ok=client.post('/api/research/provider-canary',headers=auth,json={
        'provider':'github','consent':True})
    assert ok.status_code==200 and ok.json()['status']=='empty'


def test_explicit_locale_validation_for_search_context():
    from app.v5 import WebSearchInput
    from app.main import ChatMessage
    from pydantic import ValidationError
    assert WebSearchInput(freshness='pw',country='IN',search_lang='hi').freshness=='pw'
    assert ChatMessage(question='Public historical claims',freshness='py',country='IN').country=='IN'
    try:WebSearchInput(freshness='unlimited')
    except ValidationError:pass
    else:raise AssertionError('Invalid Brave freshness accepted')
