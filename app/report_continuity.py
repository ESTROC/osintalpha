"""P0-022/023: immutable at-answer-time source snapshot for consistent reports.

Snapshots preserve the answer shown, referenced case record metadata, and linked
web leads. They are NOT truth validation or an archive of publisher pages.
"""
import hashlib
import json

def make_snapshot(conn,case_id,message_id,session_id,question,response,provider,now):
    evidence_ids=[x for x in response.get('evidenceIds',[]) if isinstance(x,str)][:12]
    bound=[]
    for eid in evidence_ids:
        row=conn.execute(
            'SELECT id,provider,label,source_url,sha256,status FROM evidence '
            'WHERE case_id=? AND id=?',(case_id,eid)).fetchone()
        if row:bound.append(dict(row))
    leads=[]
    for row in response.get('webLeads',[])[:20]:
        if isinstance(row,dict) and str(row.get('url') or '').startswith('https://'):
            leads.append({'title':str(row.get('title') or '')[:200],
                          'url':str(row['url'])[:600],'pageVerified':False})
    payload={'snapshotVersion':1,'question':str(question)[:2000],
             'answer':str(response.get('answer') or '')[:7500],
             'provider':str(provider),'evidence':bound,'webLeads':leads,
             'sessionId':session_id,'messageId':message_id,'createdAt':now,
             'claimsIndependentlyVerified':False,
             'identitiesIndependentlyVerified':False,
             'limitation':('Snapshot preserves what the user saw and cited when '
               'saved; text presence or a citation URL does not establish truth.')}
    packed=json.dumps(payload,ensure_ascii=False,sort_keys=True)
    digest=hashlib.sha256(packed.encode('utf-8')).hexdigest()
    conn.execute(
        'INSERT INTO research_response_snapshots VALUES (?,?,?,?,?,?,?)',
        (message_id,case_id,session_id,message_id,packed,digest,now))
    return payload

def latest_snapshot(conn,case_id):
    row=conn.execute(
       'SELECT snapshot_json,content_sha256 FROM research_response_snapshots '
       'WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(case_id,)).fetchone()
    if row:
        packed=row['snapshot_json']
        integrity=hashlib.sha256(packed.encode('utf-8')).hexdigest()==row['content_sha256']
        payload=json.loads(packed)
        payload['snapshotIntegrityOk']=integrity
        payload['snapshotSha256']=row['content_sha256']
        return payload
    # Old cases have no immutable snapshot; explicitly identify a legacy view.
    old=conn.execute(
        'SELECT m.id,m.session_id,m.content,m.provider,m.web_leads_json,m.created_at '
        'FROM research_messages m JOIN research_sessions s ON s.id=m.session_id '
        "WHERE s.case_id=? AND m.role='assistant' "
        'ORDER BY m.created_at DESC,m.message_index DESC LIMIT 1',(case_id,)).fetchone()
    if not old:return None
    try:leads=json.loads(old['web_leads_json'] or '[]')
    except (ValueError,TypeError):leads=[]
    return {'snapshotVersion':0,'answer':old['content'],'provider':old['provider'],
        'webLeads':leads,'createdAt':old['created_at'],'evidence':[],
        'snapshotIntegrityOk':None,'claimsIndependentlyVerified':False,
        'limitation':'Legacy chat output: no contemporaneous citation snapshot exists.'}
