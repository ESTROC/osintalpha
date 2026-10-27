"""Case-scoped PUBLIC candidate graph, not real-person entity resolution.

Cross-source matching public usernames are lead hypotheses, never account
ownership, identity verification or an automatic person merge.
"""
from __future__ import annotations
import re
from collections import defaultdict
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from typing import Literal
from . import db,main as core
router=APIRouter()
KIND=Literal['github_handle','stackoverflow_user','orcid','doi','lei','public_org_registration']
PUBLIC_KINDS=('github_handle','stackoverflow_user','orcid','doi','lei','public_org_registration')

def normalize(kind,value):
    v=str(value or '').strip()
    if kind=='github_handle':
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?',v):
            raise ValueError('Invalid public GitHub username')
        return v.casefold()
    if kind=='stackoverflow_user':
        if not re.fullmatch(r'[1-9][0-9]{0,15}',v):raise ValueError('Invalid public Stack Overflow user ID')
        return v
    if kind=='orcid':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]',v):
            raise ValueError('Invalid ORCID format')
        digits=v.replace('-','');total=0
        for d in digits[:-1]:total=(total+int(d))*2
        remainder=(12-(total%11))%11
        check='X' if remainder==10 else str(remainder)
        if digits[-1]!=check:raise ValueError('ORCID check digit mismatch')
        return v
    if kind=='doi':
        if not re.fullmatch(r'10\.[0-9]{4,9}/[^\s<>]{1,160}',v,re.I):
            raise ValueError('Invalid DOI')
        return v.casefold()
    if kind=='lei':
        if not re.fullmatch(r'[A-Z0-9]{20}',v.upper()):
            raise ValueError('Invalid LEI format')
        letters=''.join(str(ord(c)-55) if c.isalpha() else c for c in v.upper())
        if int(letters)%97!=1:raise ValueError('LEI check digits mismatch')
        return v.upper()
    if kind=='public_org_registration':
        if not re.fullmatch(r'[A-Za-z0-9/-]{6,35}',v):
            raise ValueError('Invalid public company registration candidate')
        return v.upper()
    raise ValueError('Unsupported identifier kind')

class PublicIdentifierInput(BaseModel):
    profile_id:str=Field(min_length=6,max_length=80)
    evidence_id:str=Field(min_length=6,max_length=80)
    kind:KIND
    value:str=Field(min_length=2,max_length=200)
    source_url:str=Field(min_length=12,max_length=600)

@router.post('/api/cases/{case_id}/public-identifiers',status_code=201)
def add_public_identifier(case_id:str,body:PublicIdentifierInput,
                          actor=Depends(core.protect)):
    try:canonical=normalize(body.kind,body.value)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    url=urlsplit(body.source_url)
    if url.scheme!='https' or not url.hostname or url.username or url.password:
        raise HTTPException(422,'Original HTTPS public source required')
    host=url.hostname.casefold()
    if body.kind=='github_handle':
        if host not in {'github.com','www.github.com'} or (
           (url.path.strip('/').split('/') or [''])[0].casefold()!=canonical):
            raise HTTPException(422,'Public GitHub handle must match its profile URL.')
    if body.kind=='stackoverflow_user':
        if host not in {'stackoverflow.com','www.stackoverflow.com'} or not url.path.startswith('/users/'+canonical+'/'):
            raise HTTPException(422,'Public Stack Overflow ID must match its official profile URL.')
    if body.kind=='orcid':
        if host!='orcid.org' or url.path.strip('/')!=canonical:
            raise HTTPException(422,'ORCID must link to its canonical public record.')
    if body.kind=='lei':
        if host not in {'search.gleif.org','api.gleif.org'}:
            raise HTTPException(422,'LEI record needs an original GLEIF source.')

    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        candidate=c.execute('SELECT id FROM candidate_profiles WHERE id=? AND case_id=?',
                            (body.profile_id,case_id)).fetchone()
        if not candidate:raise HTTPException(422,'Candidate is outside the case')
        evidence=c.execute('SELECT id,source_url,status FROM evidence WHERE id=? AND case_id=?',
                           (body.evidence_id,case_id)).fetchone()
        if not evidence or evidence['status']=='rejected':
            raise HTTPException(422,'Source is missing, rejected, or belongs to another case')
        if evidence['source_url']!=body.source_url:
            raise HTTPException(422,'Identifier attribution must match the saved original source URL')
        record=core.uid()
        try:
            c.execute('INSERT INTO candidate_public_identifiers VALUES (?,?,?,?,?,?,?,?,?,?)',
               (record,case_id,body.profile_id,body.evidence_id,body.kind,
                canonical,body.source_url,'unverified_identifier',actor['id'],core.iso_now()))
        except Exception as exc:
            if 'unique' in str(exc).lower() or 'duplicate' in str(exc).lower():
                raise HTTPException(409,'This identifier and source have already been linked') from exc
            raise
    core.write_audit(actor['id'],'candidate_public_identifier','case',case_id,record)
    return {'id':record,'canonicalValue':canonical,'status':'unverified_identifier',
            'personIdentityVerified':False,'accountOwnershipVerified':False}

def graph(conn,case_id):
    profiles=[dict(r) for r in conn.execute(
      'SELECT id,display_name,classification,reason FROM candidate_profiles WHERE case_id=? ORDER BY updated_at DESC,id',(case_id,))]
    ids=[dict(r) for r in conn.execute(
      'SELECT id,profile_id,evidence_id,kind,canonical_value,asserted_url,review_state '
      'FROM candidate_public_identifiers WHERE case_id=? ORDER BY kind,canonical_value',(case_id,))]
    links=[dict(r) for r in conn.execute(
      'SELECT ce.profile_id,ce.evidence_id,e.provider,e.label,e.status,e.source_url '
      'FROM candidate_evidence ce JOIN candidate_profiles p ON p.id=ce.profile_id '
      'JOIN evidence e ON e.id=ce.evidence_id '
      'WHERE p.case_id=? AND e.case_id=?',(case_id,case_id))]
    by_profile=defaultdict(list)
    for r in ids:by_profile[r['profile_id']].append(r)
    for p in profiles:
        p['identifiers']=by_profile[p['id']]
        p['sourceLeads']=[x for x in links if x['profile_id']==p['id']]
        p['independentlyVerifiedIdentity']=False
    buckets=defaultdict(set)
    for r in ids:buckets[(r['kind'],r['canonical_value'])].add(r['profile_id'])
    suggestions=[]
    for (kind,value),members in buckets.items():
        if len(members)>1:suggestions.append(
           {'kind':kind,'canonicalValue':value,'candidateIds':sorted(members),
            'decision':'manual_review_required','autoMerge':False,
            'proofOfSharedHumanIdentity':False})
    return {'candidates':profiles,'sharedIdentifierHypotheses':suggestions,
        'relationshipsVerified':False,'autoMergeEnabled':False,
        'dataSource':'Saved source-linked candidate/public-identifier graph; no person-level canonical truth.',
        'privacy':'Private phone/email, home address and government personal numbers unsupported.'}

@router.get('/api/cases/{case_id}/candidate-graph')
def candidate_graph(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        return graph(c,case_id)

@router.get('/api/cases/{case_id}/linkedin-index-notice')
def linkedin_index_notice(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        core.case_or_404(c,case_id,actor)
        rows=[dict(r) for r in c.execute(
          "SELECT id,source_url,label,status FROM evidence WHERE case_id=? "
          "AND source_url LIKE 'https://%linkedin.com/%' ORDER BY fetched_at DESC LIMIT 30",(case_id,))]
    rows=[r for r in rows if (
        (urlsplit(r['source_url']).hostname or '').casefold()=='linkedin.com' or
        (urlsplit(r['source_url']).hostname or '').casefold().endswith('.linkedin.com'))]
    return {'indexedLinks':[{'id':r['id'],'url':r['source_url'],
                 'label':r['label'],'reviewStatus':r['status'],
                 'liveLinkedInRecordVerified':False,'employmentVerified':False} for r in rows],
        'linkedinMemberOAuthIntegrated':False,'linkedinPartnerAccessIntegrated':False,
        'privateResumeDataAvailable':False,
        'notice':'Public index snippets are leads, not consented API records, employment history or account ownership.'}
