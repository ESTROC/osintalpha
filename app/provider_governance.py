"""Provider terms register and jurisdiction disclosures; no rights inferred from public API."""
from __future__ import annotations
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
from .connectors import CATALOG
router=APIRouter()
COVERAGE={
 'github':('global_public_accounts','No national legal/person registry authority'),
 'stackoverflow':('global_public_accounts','No national legal/person registry authority'),
 'openalex':('global_research_metadata','Author matching is not an employment or education certification'),
 'crossref':('global_publication_metadata','A DOI is not a verified person identity'),
 'gleif':('global_lei_coverage','LEI data covers only participating entities, varies by jurisdiction'),
 'wikipedia':('global_encyclopedia','Publisher editorial records are not an official registry'),
 'wikidata':('global_knowledge_graph','Community edits may be incomplete or disputed'),
 'gdelt':('global_news_index','Indexed news has no verified identity ownership or legal authority'),
}
PROVIDERS={p.id for p in CATALOG}

class RightsReview(BaseModel):
    status:Literal['not_reviewed','restricted','approved_limited']
    permitted_uses:list[Literal['live_queries','store_metadata','store_excerpt','display_media']]=Field(default_factory=list,max_length=4)
    terms_url:str=Field(min_length=15,max_length=450)
    reviewer_note:str=Field(min_length=40,max_length=750)

@router.get('/api/research/provider-governance')
def provider_governance(actor=Depends(core.actor_from_cookie)):
    with db.connect() as c:
        reviews={r['provider']:dict(r) for r in c.execute('SELECT * FROM provider_terms_reviews')}
    return {'items':[{'id':p.id,'name':p.title,'countryCoverage':COVERAGE[p.id][0],
       'jurisdictionAuthority':COVERAGE[p.id][1],
       'rightsStatus':reviews.get(p.id,{}).get('rights_status','not_reviewed'),
       'approvedPurposes':reviews.get(p.id,{}).get('permitted_uses',''),
       'termsReference':reviews.get(p.id,{}).get('terms_url'),
       'rightsVerifiedByLegal':False,
       'coverageVerified':False} for p in CATALOG],
       'notice':'Provider terms need independent legal review; no automated source permission or local jurisdiction claim.'}

@router.put('/api/research/provider-governance/{provider}')
def update_provider_rights(provider:str,body:RightsReview,actor=Depends(core.protect)):
    core.admin_only(actor)
    if provider not in PROVIDERS:raise HTTPException(404,'Unsupported provider.')
    from .v5 import public_https
    if not public_https(body.terms_url):
        raise HTTPException(422,'Link to accessible public official terms document required.')
    if body.status!='approved_limited' and body.permitted_uses:
        raise HTTPException(422,'Permissions require an explicit limited-approval record.')
    with db.connect() as c:
        c.execute('DELETE FROM provider_terms_reviews WHERE provider=?',(provider,))
        c.execute('INSERT INTO provider_terms_reviews VALUES (?,?,?,?,?,?,?)',
          (provider,body.status,','.join(sorted(set(body.permitted_uses))),
           body.terms_url,body.reviewer_note,actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'provider_rights_review','provider',provider,body.status)
    return {'provider':provider,'storedStatus':body.status,
       'contractualPermissionExternallyVerified':False,
       'notice':'An administrative review record is not a license grant from the publisher.'}
