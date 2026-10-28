"""Source attribution and claim-conflict workbench.

Analyst judgments and publisher domains are NOT independent authentication.
Never infer employment, enrolment, or culpability from an indexed snippet.
"""
from __future__ import annotations
import re
from collections import defaultdict
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from typing import Literal
from . import db,main as core
from .search_policy import publisher_group
router=APIRouter()

SourceKind=Literal['first_party_self_claim','publisher_editorial','official_institution_page',
                   'official_registry_record','user_submission','aggregator_or_search_snippet',
                   'unknown']
Ownership=Literal['subject_authored','publisher_authored','third_party_claim','unestablished']
Authentication=Literal['not_checked','publisher_website_checked','publisher_record_checked']
Relation=Literal['not_established','possible_subject','confirmed_by_analyst','different_subject']

class SourceAttribution(BaseModel):
    source_kind:SourceKind
    assertion_owner:Ownership
    publisher_authentication:Authentication='not_checked'
    relation_to_subject:Relation='not_established'
    rationale:str=Field(min_length=30,max_length=1400)

def inferred_kind(provider,url):
    p=str(provider or '').casefold()
    if p in {'brave_web','gdelt','brave_llm_context'}:
        return 'aggregator_or_search_snippet'
    if p=='analyst':return 'user_submission'
    if p in {'github','stackoverflow','openalex','crossref'}:return 'first_party_or_indexed_candidate'
    if p in {'gleif','wikidata','wikipedia'}:return 'public_dataset_candidate'
    return 'unknown'

def provenance_for(conn,case_id,evidence):
    row=conn.execute('SELECT source_kind,assertion_owner,publisher_authentication,relation_to_subject,rationale,reviewed_at '
       'FROM evidence_source_reviews WHERE case_id=? AND evidence_id=? '
       'ORDER BY reviewed_at DESC,id DESC LIMIT 1',(case_id,evidence['id'])).fetchone()
    reviewed=dict(row) if row else None
    return {'evidenceId':evidence['id'],'originalUrl':evidence['source_url'],
        'publisherHost':urlsplit(evidence['source_url']).hostname,
        'publisherGroup':publisher_group(evidence['source_url']),
        'inferredSourceClass':inferred_kind(evidence['provider'],evidence['source_url']),
        'analystSourceAttribution':reviewed,
        'publisherAuthenticatedBySystem':False,
        'subjectIdentityVerifiedBySystem':False,
        'assertedClaimNotIndependentlyVerified':True}

@router.get('/api/cases/{case_id}/source-attribution')
def source_attribution(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        records=[dict(r) for r in conn.execute(
            'SELECT id,provider,source_url FROM evidence WHERE case_id=? '
            'ORDER BY fetched_at DESC,id DESC LIMIT 400',(case_id,))]
        items=[provenance_for(conn,case_id,r) for r in records]
    return {'items':items,
        'notice':'An analyst-attributed page can be owned by an account holder, not the publisher, and is never independently verified as the subject.'}

@router.post('/api/cases/{case_id}/evidence/{evidence_id}/source-attribution',status_code=201)
def record_source_attribution(case_id:str,evidence_id:str,body:SourceAttribution,
                              actor=Depends(core.protect)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        evidence=conn.execute('SELECT id,source_url FROM evidence WHERE id=? AND case_id=?',
                              (evidence_id,case_id)).fetchone()
        if not evidence:raise HTTPException(404,'Evidence source missing from case.')
        if body.source_kind in {'official_institution_page','official_registry_record'} and (
            body.publisher_authentication=='not_checked'):
            raise HTTPException(422,'Record an explicit publisher review before categorizing this as an official-source page.')
        review_id=core.uid()
        conn.execute('INSERT INTO evidence_source_reviews VALUES (?,?,?,?,?,?,?,?,?,?)',
            (review_id,case_id,evidence_id,body.source_kind,body.assertion_owner,
             body.publisher_authentication,body.relation_to_subject,
             body.rationale.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'source_attribution_review','evidence',evidence_id,review_id)
    return {'id':review_id,'reviewed':True,'officialInstitutionVerifiedBySystem':False,
            'employmentOrEnrolmentVerified':False,
            'notice':'Human source-label review only; official-host appearance and byline do not verify employment or enrolment.'}

class InstitutionCheck(BaseModel):
    evidence_id:str=Field(min_length=4,max_length=80)
    institution_name:str=Field(min_length=3,max_length=200)
    research_claim:Literal['public_employment','public_enrolment','public_affiliation']
    review_note:str=Field(min_length=30,max_length=1400)
    official_page_reviewed:bool=False

@router.post('/api/cases/{case_id}/institution-check',status_code=201)
def institution_check(case_id:str,body:InstitutionCheck,actor=Depends(core.protect)):
    if not body.official_page_reviewed:
        raise HTTPException(422,'An analyst must review the original public institution page.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        evidence=conn.execute('SELECT id,source_url,provider FROM evidence WHERE case_id=? AND id=?',
                              (case_id,body.evidence_id)).fetchone()
        if not evidence:raise HTTPException(404,'Evidence unavailable in this case.')
        if not str(evidence['source_url']).startswith('https://'):
            raise HTTPException(422,'A direct HTTPS original public institution page is required.')
        rid=core.uid()
        # Preserve exact analyst scope and original page as an auditable check, not a fabricated official API result.
        import json
        details=json.dumps({'institution':body.institution_name,'researchClaim':body.research_claim,
            'sourceUrl':evidence['source_url'],'reviewNote':body.review_note,
            'humanCheckedPage':True,'independentlyVerified':False},ensure_ascii=False)
        conn.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (rid,case_id,actor['id'],rid,'institution_manual_page_review',
             body.institution_name,'manual_review',0,0,details,core.iso_now()))
    core.write_audit(actor['id'],'institution_page_review','case',case_id,rid)
    return {'id':rid,'independentInstitutionApiVerification':False,
            'employmentVerified':False,'studentEnrolmentVerified':False,
            'notice':'This is a review of a cited public page, not an authorised employer/university identity verification service.'}

class ConflictReview(BaseModel):
    left_claim_id:str=Field(min_length=4,max_length=80)
    right_claim_id:str=Field(min_length=4,max_length=80)
    classification:Literal['substantive_conflict','namesake_or_context_difference','not_comparable','resolved_after_original_review']
    right_of_reply:Literal['not_applicable','not_requested','pending','response_documented']
    review_note:str=Field(min_length=30,max_length=1400)

def conflicts(claims):
    groups=defaultdict(list)
    for c in claims:
        key=' '.join(re.findall(r'[\w]+',str(c['claim_text']).casefold()))
        groups[key].append(c)
    potential=[]
    for value,rows in groups.items():
        stances={r['stance'] for r in rows}
        if 'supports' in stances and any(x in stances for x in ('refutes','contradicts','disputes')):
            potential.append({'normalizedClaim':value[:250],
                'claimIds':[x['id'] for x in rows],'potentialConflict':True,
                'samePersonVerified':False,'resolved':False})
    return potential

@router.get('/api/cases/{case_id}/claim-conflicts')
def claim_conflicts(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        claims=[dict(r) for r in conn.execute(
            'SELECT id,claim_text,stance,evidence_id FROM claim_links WHERE case_id=?',
            (case_id,))]
        reviews=[dict(r) for r in conn.execute(
            'SELECT * FROM claim_conflict_reviews WHERE case_id=? ORDER BY reviewed_at DESC LIMIT 100',(case_id,))]
    return {'potentialContradictions':conflicts(claims),'humanDecisions':reviews,
       'dispositionRequiredForHighStakesClaims':True,
       'notice':'Text overlap or opposing stances alone cannot prove an actual contradiction or right-of-reply entitlement.'}

@router.post('/api/cases/{case_id}/claim-conflicts',status_code=201)
def review_conflict(case_id:str,body:ConflictReview,actor=Depends(core.protect)):
    if body.left_claim_id==body.right_claim_id:raise HTTPException(422,'Two different claims are required.')
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        pairs=[conn.execute('SELECT id FROM claim_links WHERE id=? AND case_id=?',
                            (x,case_id)).fetchone() for x in (body.left_claim_id,body.right_claim_id)]
        if not all(pairs):raise HTTPException(422,'Both claims must be in the authorized case.')
        identifier=core.uid()
        conn.execute('INSERT INTO claim_conflict_reviews VALUES (?,?,?,?,?,?,?,?,?)',
            (identifier,case_id,body.left_claim_id,body.right_claim_id,
             body.classification,body.right_of_reply,body.review_note.strip(),
             actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'claim_conflict_review','case',case_id,identifier)
    return {'id':identifier,'reviewState':body.classification,'factVerified':False}
