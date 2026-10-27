"""Optional second-engine check on a saved public-source research session.

One separate, explicitly consented Groq browser-search request. An apparent
URL/domain overlap is not verification, independent provenance or source truth.
"""
from __future__ import annotations
import json
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db, main as core
from .search_policy import publisher_group

router=APIRouter()

class SecondCheck(BaseModel):
    session_id:str=Field(min_length=8,max_length=64)
    question:str=Field(min_length=6,max_length=500)
    consent:bool=False

@router.post('/api/cases/{case_id}/cross-engine-check')
async def cross_engine_check(case_id:str,body:SecondCheck,actor=Depends(core.protect)):
    if not body.consent:
        raise HTTPException(422,'A second paid external search requires explicit consent.')
    with db.connect() as conn:
        ca=core.case_or_404(conn,case_id,actor)
        if not ca['ai_opt_in']:
            raise HTTPException(403,'Remote AI is not enabled for this investigation.')
        owned=conn.execute('SELECT owner_id FROM research_sessions WHERE id=? AND case_id=?',
                           (body.session_id,case_id)).fetchone()
        if not owned or (actor['role']!='admin' and owned['owner_id']!=actor['id']):
            raise HTTPException(404,'The source session is unavailable.')
        previous=conn.execute(
            """SELECT web_leads_json FROM research_messages
               WHERE session_id=? AND role='assistant'
               AND provider='groq' ORDER BY message_index DESC LIMIT 1""",
            (body.session_id,)).fetchone()
    if not previous:
        raise HTTPException(422,'First run a Groq answer grounded in attributed public source links.')
    try:
        candidate=json.loads(previous['web_leads_json'])
        primary=[x for x in candidate if isinstance(x,dict) and
                 str(x.get('url','')).startswith('https://')]
    except (TypeError,ValueError,KeyError):
        primary=[]
    if not primary:
        raise HTTPException(422,'The original research turn contained no attributed source URLs to compare.')
    # Separate Groq browser_search pass; it cannot use strict JSON schema.
    # The upstream URLs here are suggested by the model, not page captures.
    secondary=await core.chat(case_id,core.ChatMessage(
        question=body.question,provider='groq',web_search=True,
        brave_context=False,session_id=body.session_id),actor)
    candidates=[x for x in secondary.get('webLeads',[]) if isinstance(x,dict)]
    a={publisher_group(x['url']) for x in primary}
    b={publisher_group(x['url']) for x in candidates if x.get('url')}
    overlap=sorted((a&b)-{''})
    return {'sessionId':secondary.get('sessionId',body.session_id),
            'primaryPublisherGroups':sorted(a-{''}),
            'secondaryPublisherGroups':sorted(b-{''}),
            'overlappingPublisherGroups':overlap,
            'secondaryCandidateUrls':candidates,
            'engineUsed':'Groq browser_search after previously saved indexed-web source leads',
            'secondPassAnswer':secondary.get('answer',''),
            'independentCorroborationVerified':False,
            'notice':'Publisher hostname overlap is not verification or independent ownership. '
                     'The second model answer and URL suggestions require manual source review.'}
