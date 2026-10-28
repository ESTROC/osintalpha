"""Case-scoped review obligations and non-permission-changing investigation checklists."""
from __future__ import annotations
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()
TEMPLATES={
 'supplier_due_diligence':{'subject':'organization','sources':['official_registry','public_supplier_disclosures'],
    'checklist':['Source publisher ownership','Corporate namesake separation','Current licensing/right-to-store review','Contradictions and original records']},
 'public_event':{'subject':'organization','sources':['official_event_notice','public_institution_metadata'],
    'checklist':['Occurrence vs publication dates','Original authorized source','Publisher update or withdrawal','Reviewable source quotations']},
 'defensive_domain':{'subject':'domain','sources':['passive_dns','approved_public_advisory'],
    'checklist':['Explicit defensive scope','No active probing','Publisher freshness','False positive validation']},
 'research_organization':{'subject':'organization','sources':['official_organization_site','public_papers'],
    'checklist':['Entity boundaries','Authorship uncertainty','Independent source origin','Disputed affiliation']}
}
def queue(conn,case_id,actor_id,kind,source_id,title,note):
    row=conn.execute('SELECT task_id FROM case_review_obligations WHERE case_id=? AND trigger_kind=? AND trigger_id=?',
         (case_id,kind,source_id)).fetchone()
    if row:return row['task_id'],False
    ident=core.uid();now=core.iso_now()
    conn.execute('INSERT INTO investigation_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?)',
          (ident,case_id,title[:180],note[:2500],'awaiting_review','high',
           actor_id,'',actor_id,now,now))
    conn.execute('INSERT INTO investigation_task_events VALUES (?,?,?,?,?,?,?,?)',
          (core.uid(),ident,case_id,actor_id,'','awaiting_review',
           'System proposed review obligation, explicitly unverified.',now))
    conn.execute('INSERT INTO case_review_obligations VALUES (?,?,?,?)',(case_id,kind,source_id,ident))
    return ident,True

@router.get('/api/research/investigation-templates')
def templates(actor=Depends(core.actor_from_cookie)):
    return {'templates':[{'id':k,'version':1,**v} for k,v in TEMPLATES.items()],
       'permissionChanges':False,'legalAuthorizationOverride':False}

class AssignTemplate(BaseModel):
    template_id:str=Field(min_length=2,max_length=60)

@router.post('/api/cases/{case_id}/investigation-template')
def assign_template(case_id:str,body:AssignTemplate,actor=Depends(core.protect)):
    template=TEMPLATES.get(body.template_id)
    if not template:raise HTTPException(422,'Unknown approved investigation checklist.')
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        if case['subject_type']!=template['subject']:
            raise HTTPException(422,'This template does not match the case subject type.')
        conn.execute('INSERT OR IGNORE INTO case_investigation_templates VALUES (?,?,?,?,?)',
           (case_id,body.template_id,1,actor['id'],core.iso_now()))
        conn.execute('UPDATE case_investigation_templates SET template_id=?,version=1,selected_by=?,selected_at=? WHERE case_id=?',
           (body.template_id,actor['id'],core.iso_now(),case_id))
    core.write_audit(actor['id'],'case_template','case',case_id,body.template_id)
    return {'templateId':body.template_id,'version':1,'reviewChecklist':template['checklist'],
        'existingPurposeUnchanged':True,'existingExternalConsentUnchanged':True,
        'legalPermissionsChanged':False}

@router.get('/api/cases/{case_id}/review-obligations')
def list_obligations(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=[dict(x) for x in c.execute(
            'SELECT o.trigger_kind,o.trigger_id,o.task_id,t.status,t.assigned_to,t.created_at '
            'FROM case_review_obligations o JOIN investigation_tasks t ON t.id=o.task_id '
            'WHERE o.case_id=? ORDER BY t.created_at DESC,t.id DESC LIMIT 100',(case_id,))]
    return {'items':rows,'automaticallyVerified':False,
      'note':'Every proposed review still needs a named human task closure with explanation.'}

@router.get('/api/cases/{case_id}/feedback-quality-baseline')
def feedback_quality(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        samples=[dict(x) for x in c.execute('SELECT relevance,actor_id FROM source_feedback WHERE case_id=? LIMIT 250',
                                          (case_id,))]
    by_state={x:sum(y['relevance']==x for y in samples)
              for x in ('useful','irrelevant','wrong_subject','needs_review')}
    return {'labelsRecorded':len(samples),'labelCounts':by_state,'trainingPerformed':False,
       'heldOutCaseCount':0,'precisionLiftMeasured':None,
       'wrongSubjectFalsePositiveRateMeasured':None,
       'note':'Human feedback cannot safely auto-train or rerank identities without consented held-out evaluation and case isolation.'}
