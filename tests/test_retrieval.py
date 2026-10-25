"""Question-specific retrieval and persisted-context regressions for V5.1."""
import json
from app.retrieval import rank_case_evidence

def test_retrieval_selects_relevant_record_beyond_old_first_35_limit():
    rows=[{'id':str(i),'provider':'openalex','label':'Public article other topic',
           'summary':'Unrelated researcher record','status':'candidate','raw_json':'{}'}
          for i in range(85)]
    rows.append({'id':'target','provider':'github','label':'Engineering profile blockchain platform',
                 'summary':'Hyperledger Fabric and enterprise integration',
                 'status':'candidate','raw_json':json.dumps({'company':'Sample Systems','location':'Delhi','login':'targethandle'})})
    result,info=rank_case_evidence(rows,'Find blockchain engineering work',
                                    {'organization':'Sample Systems','city':'Delhi'},limit=35)
    assert info['totalRecords']==86
    assert result[0]['id']=='target'
    assert info['selected']==35
    assert info['method'].startswith('lexical')
    assert len({r['id'] for r in result})==35

def test_saved_chat_messages_feed_next_remote_response(client,auth,case,monkeypatch):
    from app import main
    monkeypatch.setenv('GROQ_API_KEY','test-only-not-live')
    assert client.put('/api/cases/'+case+'/ai-consent',headers=auth,json={'enabled':True}).status_code==200
    a=client.post('/api/cases/'+case+'/chat',headers=auth,
                  json={'question':'Remember that public handle example-public-123','provider':'local'})
    assert a.status_code==200,a.text
    sid=a.json()['sessionId']
    seen=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':json.dumps({
          'answer':'The public handle remains an unverified clue.',
          'evidence_ids':[],'follow_up':'','needs_disambiguation':True})}}]}
    class Fake:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,endpoint,json,headers):
            seen.extend(json['messages'])
            return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',Fake)
    r=client.post('/api/cases/'+case+'/chat',headers=auth,json={
        'provider':'groq','question':'What earlier public handle did I mention?',
        'session_id':sid,'history':[]})
    assert r.status_code==200,r.text
    assert r.json()['retrieval']['totalRecords']==0
    assert any('example-public-123' in x['content'] for x in seen if x['role']=='user')
    assert r.json()['sessionId']==sid
