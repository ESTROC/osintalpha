"""P0 017: Brave Context sources persist as reviewable unverified leads."""
import json
from app import main, db, brave_context


def test_017_brave_index_leads_saved_without_licensed_snippet(client,auth,case,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-no-network')
    assert client.put(f'/api/cases/{case}/ai-consent',headers=auth,json={
        'enabled':True}).status_code==200
    source={'title':'Public example index','url':'https://example.org/public-page',
            'snippet':'DO_NOT_PERSIST_THE_COPYRIGHTED_TEXT',
            'sourceDate':'2026-10-28'}
    async def fake_retrieve(*args,**kwargs):
        return {'sources':[source], 'query':'review public example', 'searchedNow':True}
    monkeypatch.setattr(brave_context,'retrieve',fake_retrieve)
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({
            'answer':'Review the indexed leads; no identity established.',
            'evidence_ids':[], 'follow_up':'', 'needs_disambiguation':True})}}]}
    class HttpClient:
        def __init__(self,*a,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        async def post(self,*a,**kw):return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',HttpClient)
    response=client.post(f'/api/cases/{case}/chat',headers=auth,json={
        'question':'What sources are indexed?','provider':'groq','brave_context':True})
    assert response.status_code==200,response.text
    with db.connect() as conn:
        evidence=[dict(r) for r in conn.execute(
          "SELECT provider,label,summary,raw_json,status FROM evidence WHERE case_id=? "
          "AND provider='brave_llm_context'",(case,))]
        captured=conn.execute('SELECT count(*) n FROM research_grounding WHERE case_id=?',
                              (case,)).fetchone()['n']
    assert len(evidence)==1 and captured==1
    assert evidence[0]['status']=='candidate'
    assert 'DO_NOT_PERSIST' not in evidence[0]['summary']
    assert 'DO_NOT_PERSIST' not in evidence[0]['raw_json']
    assert json.loads(evidence[0]['raw_json'])['page_fetched'] is False
