"""Safe, explicit link-health probes of preapproved public hosts.

No URL is declared deleted merely because a server is blocked, rate limited,
or times out. No redirects, arbitrary hosts, background crawling, or bulk scans.
"""
from __future__ import annotations
import httpx
from fastapi import APIRouter,Depends,HTTPException
from . import db,main as core
from .v5 import capture_allowed
router=APIRouter()

def classify_http(status):
    if status in (404,410):
        return 'source_not_found_on_this_check'
    if status==200:return 'responding'
    if status in (401,403,429,405):
        return 'access_or_method_restricted'
    if 300<=status<400:return 'redirect_not_followed'
    if status>=500:return 'server_error_not_source_absence'
    return 'inconclusive'

@router.post('/api/cases/{case_id}/evidence/{evidence_id}/check-url')
async def check_url(case_id:str,evidence_id:str,actor=Depends(core.protect)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        evidence=c.execute('SELECT id,source_url FROM evidence WHERE id=? AND case_id=?',
                           (evidence_id,case_id)).fetchone()
        if not evidence:raise HTTPException(404,'Case evidence not found')
        count=c.execute('SELECT count(*) n FROM source_link_checks WHERE case_id=? AND evidence_id=?',
                        (case_id,evidence_id)).fetchone()['n']
        if count>=50:raise HTTPException(429,'Per-evidence link-check limit reached')
    url=evidence['source_url']
    if not capture_allowed(url):
        raise HTTPException(422,'Link probe is limited to approved public-host allowlist; inspect other originals manually.')
    status=None
    result='network_unavailable'
    try:
        async with httpx.AsyncClient(timeout=8,follow_redirects=False,trust_env=False) as client:
            response=await client.head(url,headers={'User-Agent':'OSINTAlpha/8.0-public-link-check'})
            status=response.status_code
            result=classify_http(status)
    except httpx.HTTPError:
        result='network_unavailable'
    check_id=core.uid()
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        c.execute('INSERT INTO source_link_checks VALUES (?,?,?,?,?,?,?,?,?,?)',
                  (check_id,case_id,evidence_id,url,'HEAD',status,result,
                   'public_link_probe',core.iso_now(),actor['id']))
    core.write_audit(actor['id'],'public_link_check','evidence',evidence_id,result)
    return {'id':check_id,'url':url,'httpStatus':status,'checkState':result,
        'publisherPageVerified':False,'sourceDeletedProven':False,
        'limitation':'HEAD status is a point-in-time response, not proof of page authorship or persistent deletion.'}

@router.get('/api/cases/{case_id}/evidence/{evidence_id}/link-checks')
def link_history(case_id:str,evidence_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        if not c.execute('SELECT id FROM evidence WHERE case_id=? AND id=?',
                        (case_id,evidence_id)).fetchone():
            raise HTTPException(404,'Case source not found.')
        rows=[dict(x) for x in c.execute(
          'SELECT id,original_url,http_status,check_state,checked_at FROM source_link_checks '
          'WHERE case_id=? AND evidence_id=? ORDER BY checked_at DESC,id DESC LIMIT 50',
          (case_id,evidence_id))]
    return {'items':rows,'notFoundIsDeletionProof':False,
            'notice':'Publisher pages can disappear or change; a current HTTP response does not validate historical content.'}
