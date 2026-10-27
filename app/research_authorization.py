"""Case-level scope and owner-reviewed authorization records (P0-013).

An admin entry is an internal attestation, not independent legal approval.
The optional enforcement flag is OFF until owner-approved UX/data migration.
"""
from __future__ import annotations
import os
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import main as core,db

router=APIRouter()
CATEGORY=Literal['client_mandate','informed_consent','internal_public_research',
                 'statutory_mandate','other_documented_basis']

class ScopeApproval(BaseModel):
    specific_scope:str=Field(min_length=20,max_length=1000)
    authorization_category:CATEGORY
    approval_reference:str=Field(min_length=8,max_length=160)
    retention_days:int=Field(ge=1,le=365)
    approve:bool=False


def recorded_approval(conn,case_id):
    row=conn.execute(
      'SELECT specific_scope,authorization_category,approval_reference,'
      'retention_days,approved_by,approved_at,purpose_snapshot '
      'FROM case_research_approvals WHERE case_id=? ORDER BY approved_at DESC,id DESC LIMIT 1',
      (case_id,)).fetchone()
    return dict(row) if row else None


def require_scope_if_enabled(conn,case_id):
    if os.getenv('OSINTALPHA_ENFORCE_CASE_SCOPE','').strip()!='1':
        return
    if not recorded_approval(conn,case_id):
        raise HTTPException(403,
          'This case requires an administrator-reviewed purpose, authorization '
          'reference and retention policy before external research.')


@router.get('/api/cases/{case_id}/authorization')
def get_authorization(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        approval=recorded_approval(conn,case_id)
    return {'recordedApproval':approval,
      'requiresApprovalBeforeExternalResearch':os.getenv(
          'OSINTALPHA_ENFORCE_CASE_SCOPE','').strip()=='1',
      'approvedForEnforcedWorkflow':bool(approval),
      'independentLegalAuthorizationVerified':False,
      'notice':'An internal attestation does not establish client, legal or regulatory authorization.'}


@router.post('/api/cases/{case_id}/authorization')
def approve_scope(case_id:str,body:ScopeApproval,actor=Depends(core.protect)):
    if actor['role']!='admin':
        raise HTTPException(403,'Only an administrator can review and approve case scope.')
    if not body.approve:
        raise HTTPException(422,'Explicit administrator approval is required.')
    if body.specific_scope.strip().casefold() in {
          'authorized research','general research','research on people',
          'investigation','public information research'}:
        raise HTTPException(422,'Record a specific assignment scope, not a generic purpose.')
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        conn.execute(
          'INSERT INTO case_research_approvals VALUES (?,?,?,?,?,?,?,?,?)',
          (core.uid(),case_id,actor['id'],case['purpose'],
           body.specific_scope.strip(),body.authorization_category,
           body.approval_reference.strip(),body.retention_days,core.iso_now()))
    core.write_audit(actor['id'],'approve_scope','case',case_id,
       body.authorization_category+': retention '+str(body.retention_days)+' days')
    return {'recorded':True,'legalBasisIndependentlyVerified':False,
       'notice':'Internal administrator approval is logged, not an external legal determination.'}
