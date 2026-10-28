"""Reviewed event, organization-edge and public business/place observations only.

The system never converts retrieval time to event time or maps person locations.
"""
from __future__ import annotations
from datetime import date
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

class EventAnnotation(BaseModel):
    evidence_id:str
    capture_id:str
    exact_quote:str=Field(min_length=15,max_length=500)
    event_label:str=Field(min_length=5,max_length=180)
    observed_date:date|None=None
    published_date:date|None=None
    review_note:str=Field(min_length=20,max_length=500)

@router.post('/api/cases/{case_id}/public-events',status_code=201)
def add_event(case_id:str,body:EventAnnotation,actor=Depends(core.protect)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        cap=conn.execute('SELECT extracted_text FROM source_captures WHERE case_id=? AND evidence_id=? AND id=?',
            (case_id,body.evidence_id,body.capture_id)).fetchone()
        if not cap:raise HTTPException(404,'Original source capture not found in this case.')
        if body.exact_quote not in cap['extracted_text']:
            raise HTTPException(422,'Event quotation must exactly occur in the saved source text.')
        eid=core.uid()
        conn.execute('INSERT INTO case_public_events VALUES (?,?,?,?,?,?,?,?,?,?,?)',
           (eid,case_id,body.evidence_id,body.capture_id,body.exact_quote,
            body.observed_date.isoformat() if body.observed_date else None,
            body.published_date.isoformat() if body.published_date else None,
            body.event_label.strip(),body.review_note.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'event_source_review','case',case_id,eid)
    return {'id':eid,'eventIndependentlyVerified':False}

@router.get('/api/cases/{case_id}/chronology')
def chronology(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        events=[dict(x) for x in c.execute(
            'SELECT a.*,e.source_url,e.fetched_at,e.observed_at,e.reviewed_at '
            'FROM case_public_events a JOIN evidence e ON e.id=a.evidence_id AND e.case_id=a.case_id '
            'WHERE a.case_id=? ORDER BY a.reviewed_at DESC,a.id DESC LIMIT 200',(case_id,))]
        other=[dict(x) for x in c.execute(
            'SELECT id,label,source_url,fetched_at,observed_at,reviewed_at FROM evidence '
            'WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT 200',(case_id,))]
    items=[{'id':x['id'],'title':x['event_label'],'eventDate':x['observed_date'],
       'publicationDate':x['published_date'],'retrievalDate':x['fetched_at'],
       'sourceObservedDate':x['observed_at'],'reviewDate':x['reviewed_at'],
       'quotedPassage':x['quoted_passage'],'sourceUrl':x['source_url'],
       'dateVerification':'analyst_interpreted_source_quote','eventIndependentlyVerified':False}
       for x in events]
    referenced={x['evidence_id'] for x in events}
    for x in other:
        if x['id'] in referenced:continue
        items.append({'id':x['id'],'title':x['label'],'eventDate':None,
           'publicationDate':None,'retrievalDate':x['fetched_at'],
           'sourceObservedDate':x['observed_at'],'reviewDate':x['reviewed_at'],
           'quotedPassage':None,'sourceUrl':x['source_url'],
           'dateVerification':'retrieval_only_not_event','eventIndependentlyVerified':False})
    return {'items':items,'coverageLimited':len(other)==200,
      'warning':'Retrieval, publication, review and alleged occurrence dates are distinct. Unknown event date stays null.'}

class RelationTime(BaseModel):
    left_kind:Literal['organization','business','public_institution']='organization'
    right_kind:Literal['organization','business','public_institution']='organization'
    valid_from:date|None=None
    valid_until:date|None=None
    contradiction_note:str=Field(min_length=20,max_length=500)

@router.put('/api/cases/{case_id}/organization-links/{relation_id}/dates')
def set_org_relation_dates(case_id:str,relation_id:str,body:RelationTime,
       actor=Depends(core.protect)):
    if body.valid_from and body.valid_until and body.valid_from>body.valid_until:
        raise HTTPException(422,'Relationship date interval is invalid.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        row=conn.execute('SELECT r.id,r.review_state,e.status source_status FROM sourced_relationships r '
          'JOIN evidence e ON e.id=r.evidence_id AND e.case_id=r.case_id '
          'WHERE r.id=? AND r.case_id=?',(relation_id,case_id)).fetchone()
        if not row:raise HTTPException(404,'Case relationship was not found.')
        if row['review_state'] not in ('reviewed_public_record','disputed'):
            raise HTTPException(422,'Review original record before adding a dated relationship.')
        if row['review_state']=='reviewed_public_record' and row['source_status']!='corroborated':
            raise HTTPException(422,'A reviewed organization relation requires a corroborated case source.');
        conn.execute('DELETE FROM organization_relation_dates WHERE relation_id=?',(relation_id,))
        conn.execute('INSERT INTO organization_relation_dates VALUES (?,?,?,?,?,?,?,?,?)',
            (relation_id,case_id,body.left_kind,body.right_kind,
             body.valid_from.isoformat() if body.valid_from else None,
             body.valid_until.isoformat() if body.valid_until else None,
             body.contradiction_note.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'org_relation_date_review','case',case_id,relation_id)
    return {'dated':True,'organizationOwnershipVerified':False}

@router.get('/api/cases/{case_id}/organization-links')
def org_links(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        links=[dict(x) for x in conn.execute(
            'SELECT r.id,r.left_name,r.right_name,r.relationship,r.review_state,r.reviewed_at,'
            'r.evidence_id,e.source_url,d.valid_from,d.valid_until,d.contradiction_note '
            'FROM sourced_relationships r JOIN evidence e ON e.id=r.evidence_id AND e.case_id=r.case_id '
            'JOIN organization_relation_dates d ON d.relation_id=r.id AND d.case_id=r.case_id '
            "WHERE r.case_id=? AND ((r.review_state='reviewed_public_record' AND e.status='corroborated') OR r.review_state='disputed') "
            'ORDER BY r.reviewed_at DESC,r.id DESC LIMIT 150',(case_id,))]
    return {'edges':links,'unrelatedEntitiesLinked':False,'legalRelationshipsVerified':False,
        'notice':'Edges are human-reviewed source claims, not independently certified legal ownership or a person graph.'}

class PublicPlace(BaseModel):
    evidence_id:str
    place_name:str=Field(min_length=4,max_length=160)
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
    publisher_date:date|None=None
    precision:Literal['publisher_public_point','publisher_public_area']
    review_status:Literal['reviewed_public_location','disputed_location']
    annotation:str=Field(min_length=30,max_length=600)

@router.post('/api/cases/{case_id}/public-org-places',status_code=201)
def add_public_place(case_id:str,body:PublicPlace,actor=Depends(core.protect)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        if case['subject_type']!='organization':
            raise HTTPException(422,'Coordinates are supported only for public organizations/places, never person research.')
        source=conn.execute('SELECT id,status FROM evidence WHERE id=? AND case_id=?',
                            (body.evidence_id,case_id)).fetchone()
        if not source:raise HTTPException(404,'Source not found in case.')
        if source['status']!='corroborated':
            raise HTTPException(422,'Publisher location source must receive prior analyst review.')
        ident=core.uid()
        conn.execute('INSERT INTO public_org_place_points VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (ident,case_id,body.evidence_id,body.place_name,body.latitude,body.longitude,
             body.publisher_date.isoformat() if body.publisher_date else None,
             body.precision,body.review_status,body.annotation.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'public_organization_place','case',case_id,ident)
    return {'id':ident,'personTracking':False,'publisherCoordinatesIndependentlyVerified':False}

@router.get('/api/cases/{case_id}/public-org-places')
def public_places(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        records=[dict(x) for x in conn.execute(
            'SELECT p.id,p.place_name,p.latitude,p.longitude,p.publisher_date,p.precision,'
            'p.review_status,p.evidence_id,e.source_url FROM public_org_place_points p '
            'JOIN evidence e ON e.id=p.evidence_id AND e.case_id=p.case_id '
            'WHERE p.case_id=? ORDER BY p.recorded_at DESC,p.id DESC LIMIT 100',(case_id,))]
    return {'points':[x for x in records if x['review_status']=='reviewed_public_location'],
       'disputedWithheld':sum(x['review_status']=='disputed_location' for x in records),
       'individualPersonLocationInferred':False,'notes':'Only reviewed public organization points; not verified person locations.'}
