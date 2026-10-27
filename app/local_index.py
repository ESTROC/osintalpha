"""Case-scoped index over previously saved public sources.

It is NOT a web-scale search engine, not a Google replacement, and not an
identity resolution service. Factual truth requires independent review.
"""
from __future__ import annotations
import re
from fastapi import APIRouter,Depends,Query
from . import db,main as core
from .search_policy import balance_results

router=APIRouter()
_STOP={'the','what','when','where','who','which','how','with','have','about',
       'from','this','public','source','record','find','research'}

def index_terms(value):
    return {x for x in re.findall(r'[a-z0-9_]{3,}',str(value or '').casefold())
            if x not in _STOP}

@router.get('/api/cases/{case_id}/local-source-index')
def search_saved_public_index(case_id:str,q:str=Query(min_length=3,max_length=200),
                               limit:int=Query(default=20,ge=1,le=40),
                               actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
            '''SELECT id,provider,label,summary,source_url,status,fetched_at
               FROM evidence WHERE case_id=? AND status!='rejected'
               ORDER BY fetched_at DESC LIMIT 1000''',(case_id,))]
    requested=index_terms(q)
    scored=[]
    for record in rows:
        matched=requested&index_terms(record['label']+' '+record['summary'])
        if not matched:continue
        scored.append((len(matched),record))
    scored.sort(key=lambda pair:(-pair[0],pair[1]['id']))
    selected=balance_results([{
        'url':r['source_url'],'id':r['id'],'provider':r['provider'],
        'label':r['label'],'summary':r['summary'][:400],
        'reviewStatus':r['status'],'matchedTerms':sorted(requested&index_terms(r['label']+' '+r['summary'])),
        'fetchedAt':r['fetched_at']}
        for _,r in scored],max_per_site=5,limit=limit)
    return {'query':q,'items':selected,'storedRecordsChecked':len(rows),
            'matchedStoredRecords':len(scored),'scope':'case_saved_sources_only',
            'searchedGlobalWeb':False,'hasIndependentIndex':False,
            'identityVerified':False,
            'notice':'Only existing saved case records are searched; external web coverage is not implied.'}
