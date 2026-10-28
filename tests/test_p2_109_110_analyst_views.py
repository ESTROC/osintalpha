"""P2 109–110: authenticated immutable provenance diffs and stable page navigation."""
import hashlib,json
from app import db
from app.report_continuity import make_snapshot

def test_cursor_thousand_records_no_duplicates(client,auth,case):
    with db.connect() as c:
        for i in range(1000):
            uid=f'{i:024x}'
            c.execute('INSERT INTO evidence (id,case_id,provider,label,summary,source_url,source_ref,'
             'fetched_at,observed_at,sha256,status,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
             (uid,case,'synthetic',f'Record {i}','Source candidate',
              f'https://example.org/{i}',f'candidate-{i}','2026-10-28T12:00:00Z',None,
              'f'*64,'candidate','{}'))
    seen=set();cursor=None
    for i in range(21):
        endpoint=f'/api/cases/{case}/evidence-cursor?limit=53'
        if cursor:endpoint+='&cursor='+cursor
        resp=client.get(endpoint)
        assert resp.status_code==200,resp.text
        data=resp.json()
        for item in data['items']:
            assert item['id'] not in seen
            seen.add(item['id'])
        cursor=data['nextCursor']
        if not cursor:break
    assert len(seen)==1000 and cursor is None
    assert client.get(f'/api/cases/{case}/evidence-cursor?limit=30&cursor=garbage').status_code==422

def test_provenance_diff_preserves_baseline_and_handles_dropped_citation(client,auth,case):
    with db.connect() as c:
        owner=c.execute('SELECT created_by FROM cases WHERE id=?',(case,)).fetchone()['created_by']
        c.execute('INSERT INTO research_sessions VALUES (?,?,?,?,?,?)',
                  ('diff-session',case,owner,'Synthetic','2026-10-28','2026-10-28'))
        for i,word in enumerate(('Earlier answer','Later answer')):
            mid='diff-message-'+str(i)
            c.execute('INSERT INTO research_messages VALUES (?,?,?,?,?,?,?,?,?)',
             (mid,'diff-session','assistant',word,'local','[]','[]','2026-10-28T11:00:00Z',i))
            make_snapshot(c,case,mid,'diff-session','Synthetic research question',
              {'answer':word,'evidenceIds':[]},'local','2026-10-28T11:00:00Z')
    res=client.get(f'/api/cases/{case}/answer-snapshot-diff?left_message=diff-message-0&right_message=diff-message-1')
    assert res.status_code==200,res.text
    body=res.json()
    assert body['answerTextDiff']
    assert body['retractedFacts']==[] and not body['meaningVerified']
    assert client.get(f'/api/cases/{case}/answer-snapshot-diff?left_message=diff-message-0&right_message=absent').status_code==404
