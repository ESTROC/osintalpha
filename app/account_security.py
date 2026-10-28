"""Administrative account lifecycle; password changes require knowledge of current secret.

No phishing-resistant MFA or organization SSO: state this prominently rather than
misrepresent password-only security as enterprise authentication.
"""
from __future__ import annotations
import hmac,os
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class ChangePassword(BaseModel):
    current_password:str=Field(min_length=1,max_length=300)
    new_password:str=Field(min_length=16,max_length=160)

class AdminCredentialReset(BaseModel):
    administrator_password:str=Field(min_length=1,max_length=300)
    temporary_password:str=Field(min_length=16,max_length=160)

class AccountStatus(BaseModel):
    active:bool
    administrator_password:str=Field(min_length=1,max_length=300)

def require_admin_current_password(conn,actor,pwd):
    core.admin_only(actor)
    row=conn.execute('SELECT passhash,salt FROM users WHERE id=? AND active=1',
                     (actor['id'],)).fetchone()
    if not row or not db.verify_password(pwd,row):
        raise HTTPException(403,'Administrator credential confirmation failed.')

def reject_unsafe_new_secret(current,new):
    if new==current:raise HTTPException(422,'New secret must differ from current secret.')
    if len(new)<16 or new.casefold() in ('password12345678','changeme12345678'):
        raise HTTPException(422,'Choose a strong unique secret of at least 16 characters.')

@router.post('/api/auth/change-password')
def change_password(body:ChangePassword,actor=Depends(core.protect)):
    with db.connect() as c:
        row=c.execute('SELECT passhash,salt FROM users WHERE id=? AND active=1',(actor['id'],)).fetchone()
        if not row or not db.verify_password(body.current_password,row):
            raise HTTPException(403,'Current password is incorrect.')
        reject_unsafe_new_secret(body.current_password,body.new_password)
        salt,digest=db.hash_password(body.new_password)
        c.execute('UPDATE users SET salt=?,passhash=? WHERE id=?',(salt,digest,actor['id']))
        c.execute('DELETE FROM sessions WHERE user_id=?',(actor['id'],))
        c.execute('INSERT OR IGNORE INTO user_security_state(user_id) VALUES (?)',(actor['id'],))
        c.execute('UPDATE user_security_state SET must_change_password=0,password_changed_at=?,changed_by=? WHERE user_id=?',
                  (core.iso_now(),actor['id'],actor['id']))
    core.write_audit(actor['id'],'password_self_rotate','user',actor['id'],'all sessions revoked')
    return {'changed':True,'sessionsRevoked':True,'requiresNewLogin':True}

@router.post('/api/users/{user_id}/reset-credential')
def reset_user_password(user_id:str,body:AdminCredentialReset,actor=Depends(core.protect)):
    with db.connect() as c:
        require_admin_current_password(c,actor,body.administrator_password)
        target=c.execute('SELECT id,username FROM users WHERE id=? AND active=1',(user_id,)).fetchone()
        if not target:raise HTTPException(404,'Active account not found.')
        reject_unsafe_new_secret(body.administrator_password,body.temporary_password)
        salt,digest=db.hash_password(body.temporary_password)
        c.execute('UPDATE users SET salt=?,passhash=? WHERE id=?',(salt,digest,user_id))
        c.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
        c.execute('INSERT OR IGNORE INTO user_security_state(user_id) VALUES (?)',(user_id,))
        c.execute('UPDATE user_security_state SET must_change_password=1,password_changed_at=?,changed_by=? WHERE user_id=?',
                  (core.iso_now(),actor['id'],user_id))
    core.write_audit(actor['id'],'credential_admin_reset','user',user_id,'sessions revoked; forced self change')
    return {'reset':True,'sessionsRevoked':True,'mustChangePassword':True,
            'temporaryPasswordReturned':False,'delivery':'Out-of-band secure delivery by administrator; no email sent.'}

@router.patch('/api/users/{user_id}/status')
def update_account_status(user_id:str,body:AccountStatus,actor=Depends(core.protect)):
    if user_id==actor['id'] and not body.active:
        raise HTTPException(422,'An administrator cannot disable their own current account.')
    with db.connect() as c:
        require_admin_current_password(c,actor,body.administrator_password)
        row=c.execute('SELECT id,active,role FROM users WHERE id=?',(user_id,)).fetchone()
        if not row:raise HTTPException(404,'Account not found.')
        if not body.active and row['role']=='admin':
            other=c.execute('SELECT count(*) n FROM users WHERE active=1 AND role=? AND id!=?',
                ('admin',user_id)).fetchone()['n']
            if not other:raise HTTPException(409,'Cannot deactivate the last active administrator.')
        c.execute('UPDATE users SET active=? WHERE id=?',(int(body.active),user_id))
        if not body.active:c.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
    core.write_audit(actor['id'],'user_status','user',user_id,'active' if body.active else 'disabled; sessions revoked')
    return {'active':body.active,'sessionsRevoked':not body.active}

@router.get('/api/auth/security-capabilities')
def security_capabilities(actor=Depends(core.actor_from_cookie)):
    return {'passwordRotation':True,'adminRevocation':True,
       'phishingResistantMfa':False,'organizationSso':False,
       'enterpriseAuthenticationApproved':False,
       'warning':'Password-only login is not suitable for regulated agency production until independently reviewed phishing-resistant MFA and SSO are integrated.'}
