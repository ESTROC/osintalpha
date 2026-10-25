"""Conservative duplicate-source detection; never auto-merge identities.

Source URLs and DOI identifiers may identify the same publication or page,
not independent corroborating evidence. Similar titles are only review leads.
"""
from __future__ import annotations
import json
import re
from collections import defaultdict
from urllib.parse import urlsplit,parse_qsl,unquote,urlencode
from fastapi import APIRouter,Depends,Query
from . import db,main as core

router=APIRouter()
TRACKING={'fbclid','gclid','mc_cid','mc_eid','ref_src','igshid','yclid'}
COMMON={'the','for','and','with','from','that','this','about','using','based',
        'an','a','of','on','in','to','by','is','at','as','or','review','profile','public','candidate'}

def canonical_doi(value):
    text=str(value or '').strip()
    if not text:return ''
    if text.lower().startswith(('https://doi.org/','http://doi.org/')):
        text=urlsplit(text).path.lstrip('/')
    text=unquote(text).strip().casefold().rstrip('/')
    return text if re.fullmatch(r'10\.\d{4,9}/\S+',text) else ''

def canonical_url(value):
    try:
        p=urlsplit(str(value or ''))
        if p.scheme.lower() not in ('http','https') or not p.hostname or p.username or p.password:return ''
        host=p.hostname.casefold().rstrip('.')
        if host.startswith('www.'):host=host[4:]
        port=':'+str(p.port) if p.port and p.port not in (80,443) else ''
        path=unquote(p.path or '/').rstrip('/') or '/'
        query=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True)
               if not k.casefold().startswith('utm_') and k.casefold() not in TRACKING]
        query.sort()
        return host+port+path.casefold()+('?' + urlencode(query) if query else '')
    except (ValueError,TypeError):return ''

def title_tokens(title):
    return frozenset(w for w in re.findall(r'[a-z0-9]+',str(title or '').casefold())
                     if len(w)>=3 and w not in COMMON)

def data_identifiers(record):
    try:raw=json.loads(record.get('raw_json') or '{}')
    except (TypeError,ValueError):raw={}
    if not isinstance(raw,dict):raw={}
    doi=canonical_doi(raw.get('DOI') or raw.get('doi') or record.get('source_url'))
    return {'doi':doi,'url':canonical_url(record.get('source_url')),
            'titleTokens':title_tokens(record.get('label'))}

def detect(records,limit=60):
    meta={r['id']:data_identifiers(r) for r in records}
    by_doi=defaultdict(list);by_url=defaultdict(list)
    for r in records:
        m=meta[r['id']]
        if m['doi']:by_doi[m['doi']].append(r)
        if m['url']:by_url[m['url']].append(r)
    pairs={}
    def add(a,b,reason,rule):
        if a['id']==b['id']:return
        ordered=sorted((a,b),key=lambda x:x['id'])
        key=(ordered[0]['id'],ordered[1]['id'])
        if key not in pairs or rule=='same_doi':
            pairs[key]={'leftId':key[0],'rightId':key[1],
                       'leftLabel':ordered[0]['label'],'rightLabel':ordered[1]['label'],
                       'providers':[ordered[0]['provider'],ordered[1]['provider']],
                       'rule':rule,'reason':reason,'notIndependent':rule in ('same_doi','same_url'),
                       'identityVerified':False}
    for group in by_doi.values():
        for i,a in enumerate(group):
            for b in group[i+1:]:add(a,b,'Exact DOI identifier; one publication, not independent corroboration.','same_doi')
    for group in by_url.values():
        for i,a in enumerate(group):
            for b in group[i+1:]:add(a,b,'Canonical public URL matches; may be one underlying source.','same_url')
    # Similar titles do not establish identical people, publications or claims.
    candidates=[r for r in records if len(meta[r['id']]['titleTokens'])>=6]
    for i,a in enumerate(candidates):
        ta=meta[a['id']]['titleTokens']
        for b in candidates[i+1:]:
            if a['provider']==b['provider'] or (a['id'],b['id']) in pairs:continue
            tb=meta[b['id']]['titleTokens']
            ratio=len(ta&tb)/max(1,len(ta|tb))
            if ratio>=0.9 and len(ta&tb)>=6:
                add(a,b,'Highly similar public titles; inspect sources before deciding equivalence.','similar_title')
    order={'same_doi':0,'same_url':1,'similar_title':2}
    result=sorted(pairs.values(),key=lambda x:(order[x['rule']],x['leftId'],x['rightId']))
    return {'pairs':result[:limit],'totalPairs':len(result),
            'counts':{rule:sum(v['rule']==rule for v in result) for rule in order},
            'caveat':'Exact DOI/URL can reveal duplicate source records, not duplicate people. Similar titles are only human-review suggestions. No identities or sources are automatically merged.'}

@router.get('/api/cases/{case_id}/duplicate-sources')
def duplicate_sources(case_id:str,actor=Depends(core.actor_from_cookie),
        limit:int=Query(default=40,ge=1,le=100)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute('''SELECT id,provider,label,source_url,raw_json
             FROM evidence WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT 750''',(case_id,))]
    result=detect(rows,limit)
    result['recordsExamined']=len(rows)
    result['cappedAt']=750
    result['notice']='Duplicate suggestions do not count as independent corroborating sources.'
    return result
