"""P1 079/087: answer-time search failures and retrieved evidence are immutable on reload."""
import json
from app import db
from app.report_continuity import snapshot_metadata

def test_local_answer_snapshot_captures_query_status_and_reloads(client,auth,case):
    ev=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
      'label':'Public candidate document','summary':'An unverified source record',
      'source_url':'https://example.org/document'})
    assert ev.status_code==200,ev.text
    with db.connect() as c:
        actor_id=c.execute('SELECT created_by FROM cases WHERE id=?',(case,)).fetchone()['created_by']
        c.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        ('failed-query-079',case,actor_id,'test-run-079','brave_web','Synthetic query','error',
          0,0,'Brave unavailable (mock test)','2026-10-28T00:00:00Z'))
    chat=client.post(f'/api/cases/{case}/chat',headers=auth,json={
      'question':'Summarize what the saved public source actually supports.',
      'provider':'local'})
    assert chat.status_code==200,chat.text
    convo=client.get(f'/api/cases/{case}/conversations/{chat.json()["sessionId"]}')
    assert convo.status_code==200,convo.text
    provenance=convo.json()['messages'][-1]['provenance']
    assert provenance['integrityOk'] is True
    assert provenance['snapshotVersion']==1
    assert provenance['retrievalTraceVersion']==2
    assert provenance['searchTrace']['providerFailures'][0]['provider']=='brave_web'
    assert provenance['searchTrace']['retrievalComplete'] is False
    with db.connect() as c:
        c.execute('DELETE FROM research_queries WHERE id=?',('failed-query-079',))
    reopened=client.get(f'/api/cases/{case}/conversations/{chat.json()["sessionId"]}').json()
    assert reopened['messages'][-1]['provenance']['searchTrace']['providerFailures']

def test_snapshot_tamper_flag(client,auth,case):
    out=client.post(f'/api/cases/{case}/chat',headers=auth,
           json={'question':'What is known from cited sources?','provider':'local'})
    assert out.status_code==200,out.text
    with db.connect() as c:
        snap=c.execute('SELECT id,assistant_message_id FROM research_response_snapshots WHERE case_id=?',(case,)).fetchone()
        c.execute('UPDATE research_response_snapshots SET snapshot_json=? WHERE id=?',
                  ('{"answer":"tampered"}',snap['id']))
        result=snapshot_metadata(c,case,snap['assistant_message_id'])
    assert result['integrityOk'] is False
    assert not result['available']
