"""Explainable no-result guidance from saved research stages, never guessed truth."""
from __future__ import annotations
from fastapi import APIRouter,Depends
from . import db,main as core
router=APIRouter()

def guidance(conn,case_id):
    n=conn.execute('SELECT count(*) n FROM evidence WHERE case_id=?',(case_id,)).fetchone()['n']
    attempts=[dict(x) for x in conn.execute(
      'SELECT provider,status,returned_count FROM research_queries WHERE case_id=? '
      'ORDER BY created_at DESC,id DESC LIMIT 80',(case_id,))]
    candidates=conn.execute('SELECT count(*) n FROM candidate_profiles WHERE case_id=? '
         "AND classification IN ('potential_match','confirmed_by_analyst')",(case_id,)).fetchone()['n']
    if not attempts and not n:
        return {'reason':'never_searched','nextAction':'Start an authorized public-source search or add a published source.',
                'noHitClaim':False}
    failed=[x for x in attempts if x['status'] in ('error','failed','unavailable','blocked','fallback')]
    completed=[x for x in attempts if x['status'] in ('ok','done','completed','success','no_hits')]
    if failed and not any(x['returned_count']>0 for x in attempts):
        return {'reason':'provider_error','nextAction':'Inspect source health and retry the failed provider; use an authorized alternative. Do not treat this as no records.',
                'noHitClaim':False}
    if not n and completed:
        return {'reason':'no_returned_records','nextAction':'Add a distinguishing published clue or broaden the authorized source and date scope.',
                'noHitClaim':False}
    if candidates>1:
        return {'reason':'multiple_identity_hypotheses','nextAction':'Review each candidate separately; record disconfirming clues and original-source URLs.',
                'noHitClaim':False}
    if n:
        return {'reason':'review_required','nextAction':'Open source originals, attach exact quotations and request independent analyst review.',
                'noHitClaim':False}
    return {'reason':'provider_not_covered_or_unattempted','nextAction':'Review configured provider coverage and authorization before interpreting missing results.',
            'noHitClaim':False}

@router.get('/api/cases/{case_id}/research-next-step')
def next_step(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        result=guidance(conn,case_id)
    return {**result,'conclusionVerified':False,
      'notice':'Absence of a saved record is not evidence of absence from the public web.'}
