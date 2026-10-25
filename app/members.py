"""Explicit editor access for authorized case collaboration.

Sharing grants case editing only. It does not grant case deletion or ownership
transfer. All membership changes are audited; revoked access is immediately
enforced by the central case authorization check.
"""
from __future__ import annotations
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core

router=APIRouter()

def must_manage(conn,case_id,actor):
    record=core.case_or_404(conn,case_id,actor)
    if actor['role']!='admin' and record['created_by']!=actor['id']:
        raise HTTPException(403,'Only the case owner or an administrator may manage access.')
    return record

class MemberInput(BaseModel):
    username:str=Field(min_length=2,max_length=60)

@router.get('/api/cases/{case_id}/members')
def list_members(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        case=core.case_or_404(c,case_id,actor)
        rows=[dict(x) for x in c.execute('''SELECT m.user_id,u.username,m.granted_at
            FROM case_members m JOIN users u ON u.id=m.user_id
            WHERE m.case_id=? AND u.active=1 ORDER BY u.username''',(case_id,))]
        owner=c.execute('SELECT id,username FROM users WHERE id=?',(case['created_by'],)).fetchone()
    return {'owner':dict(owner) if owner else None,'editors':rows,
            'canManage':actor['role']=='admin' or case['created_by']==actor['id'],
            'notice':'Editors can research and review this case. Only its owner or administrators may grant access or delete the case.'}

@router.post('/api/cases/{case_id}/members',status_code=201)
def add_member(case_id:str,body:MemberInput,actor=Depends(core.protect)):
    with db.connect() as c:
        case=must_manage(c,case_id,actor)
        target=c.execute('SELECT id,username FROM users WHERE username=? AND active=1',(body.username.strip(),)).fetchone()
        if not target:raise HTTPException(422,'No active analyst with this username.')
        if target['id']==case['created_by']:raise HTTPException(422,'The owner already has access.')
        if target['id']==actor['id']:raise HTTPException(422,'You already have administrative or owner access.')
        existed=c.execute('SELECT user_id FROM case_members WHERE case_id=? AND user_id=?',
                          (case_id,target['id'])).fetchone()
        if existed:raise HTTPException(409,'Analyst already has access.')
        c.execute('INSERT INTO case_members VALUES (?,?,?,?)',
                  (case_id,target['id'],actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'case_member_add','case',case_id,body.username.strip())
    return {'ok':True,'userId':target['id']}

@router.delete('/api/cases/{case_id}/members/{user_id}')
def remove_member(case_id:str,user_id:str,actor=Depends(core.protect)):
    with db.connect() as c:
        must_manage(c,case_id,actor)
        changed=c.execute('DELETE FROM case_members WHERE case_id=? AND user_id=?',(case_id,user_id)).rowcount
        if not changed:raise HTTPException(404,'Case editor membership not found.')
    core.write_audit(actor['id'],'case_member_remove','case',case_id,user_id)
    return {'ok':True}
