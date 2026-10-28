"""P0-022/023: immutable at-answer-time source snapshot for consistent reports.

Snapshots preserve the answer shown, referenced case record metadata, and linked
web leads. They are NOT truth validation or an archive of publisher pages.
"""
import hashlib
import json

"""Durable answer-time retrieval trace; source snippets remain bounded untrusted data."""
def snapshot_search_trace(conn,case_id):
    rows=[dict(x) for x in conn.execute(
        'SELECT id,provider,query_text,status,returned_count,new_count,message,created_at '
        'FROM research_queries WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 80',(case_id,))]
    plan=conn.execute('SELECT original_question,plan_json,updated_at '
         'FROM case_search_plans WHERE case_id=?',(case_id,)).fetchone()
    try:
        p=json.loads(plan['plan_json']) if plan else {}
    except (ValueError,TypeError):
        p={}
    failure=[{'provider':x['provider'],'query':x['query_text'][:180],
              'status':x['status'],'time':x['created_at'],
              'message':x['message'][:240]} for x in rows
             if x['status'] in ('error','blocked','unavailable','failed','fallback','skipped')]
    return {'originalQuestion':plan['original_question'] if plan else None,
        'planUpdatedAt':plan['updated_at'] if plan else None,
        'selectedStructuredProviders':p.get('providers',[]),
        'sourceQueries':[{
            'provider':x['provider'],'query':x['query_text'][:180],
            'status':x['status'],'resultCount':x['returned_count'],
            'createdAt':x['created_at']} for x in rows],
        'providerFailures':failure[:30],
        'retrievalComplete':False,
        'notice':'Recorded provider calls only; any unsearched API and unavailable upstream source remain unknown.'}

def snapshot_metadata(conn,case_id,message_id):
    row=conn.execute('SELECT snapshot_json,content_sha256 FROM research_response_snapshots '
         'WHERE case_id=? AND assistant_message_id=?',(case_id,message_id)).fetchone()
    if not row:return {'available':False,'snapshotVersion':0,'integrityOk':None,
         'notice':'Legacy answer has no contemporaneous answer-time provenance snapshot.'}
    ok=hashlib.sha256(row['snapshot_json'].encode('utf-8')).hexdigest()==row['content_sha256']
    if not ok:return {'available':False,'snapshotVersion':None,'integrityOk':False,
         'notice':'Saved answer provenance hash mismatch; do not treat this record as trustworthy.'}
    try:p=json.loads(row['snapshot_json'])
    except (ValueError,TypeError):return {'available':False,'integrityOk':False}
    return {'available':True,'snapshotVersion':p.get('snapshotVersion',0),
        'integrityOk':True,'snapshotSha256':row['content_sha256'],
        'retrievalTraceVersion':p.get('retrievalTraceVersion',0),
        'question':p.get('question'),'answer':p.get('answer'),
        'evidence':p.get('evidence',[]),'webLeads':p.get('webLeads',[]),
        'searchTrace':p.get('searchTrace'),
        'retrievalContext':p.get('retrievalContext'),
        'answerGates':p.get('answerGates'),
        'createdAt':p.get('createdAt'),
        'factVerification':False}

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
    trace=snapshot_search_trace(conn,case_id)
    context=response.get('answerProvenance') if isinstance(response.get('answerProvenance'),dict) else {}
    gates={key:response.get(key) for key in ('evidenceGateAction','highRiskReview',
        'needsDisambiguation','sourceContentScreening','answerQuality') if key in response}
    payload={'snapshotVersion':1,'retrievalTraceVersion':2,'question':str(question)[:2000],
             'answer':str(response.get('answer') or '')[:7500],
             'provider':str(provider),'evidence':bound,'webLeads':leads,
             'searchTrace':trace,'retrievalContext':{
               'query':str(context.get('query') or question)[:500],
               'retrievedEvidenceIds':[str(x)[:90] for x in context.get('retrievedEvidenceIds',[])[:40]],
               'braveSourceUrls':[str(x)[:600] for x in context.get('braveSourceUrls',[])[:12]],
               'retrievalMethod':str(context.get('retrievalMethod') or 'local_saved_sources')[:80],
               'coverageWarning':'This is a record of sources sent to answer generation, not proof all sources were searched.'},
             'answerGates':gates,
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
