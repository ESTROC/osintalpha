"""Strict, readable advanced public-search operators; not unrestricted search DSL."""
from __future__ import annotations
import re,shlex
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import main as core
from .research_safety import require_safe_remote_query
router=APIRouter()

class AdvancedQuery(BaseModel):
    question:str=Field(min_length=3,max_length=200)
    exact_phrase:str=Field(default='',max_length=100)
    include_domain:str=Field(default='',max_length=100)
    exclude_terms:list[str]=Field(default_factory=list,max_length=5)
    subject_type:str=Field(default='organization')

def safe_token(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,79}',value):
        raise HTTPException(422,'Query token contains unsupported operators or characters.')
    return value.strip()

def query_preview(body):
    if body.subject_type not in ('person','organization','domain','ip'):
        raise HTTPException(422,'Unsupported subject type.')
    question=' '.join(body.question.split())
    require_safe_remote_query(question,body.subject_type)
    exact=safe_token(body.exact_phrase) if body.exact_phrase else ''
    domain=body.include_domain.strip().lower()
    if domain and not re.fullmatch(r'(?:[a-z0-9-]+\.)+[a-z]{2,24}',domain):
        raise HTTPException(422,'Source scope must be a public DNS domain only.')
    exclusions=[safe_token(x) for x in body.exclude_terms]
    if len(set(exclusions))!=len(exclusions):
        raise HTTPException(422,'Duplicate exclusions are not allowed.')
    if any(len(x.split())!=1 for x in exclusions):
        raise HTTPException(422,'Exclusions must be single safe terms.')
    parts=[question]
    if exact:parts.append('"'+exact+'"')
    if domain:parts.append('site:'+domain)
    parts.extend('-'+x for x in exclusions)
    search=' '.join(parts)
    if len(search)>200:raise HTTPException(422,'Preview exceeds 200-character provider query limit.')
    require_safe_remote_query(search,body.subject_type)
    return {'providerQuery':search,'originalQuestion':question,
        'sourceDomain':domain or None,'exactPhrase':exact or None,
        'excludedTerms':exclusions,'executeAutomatically':False,
        'identityVerified':False,
        'note':'Query preview only. External provider may interpret operators differently; inspect result provenance.'}

@router.post('/api/research/advanced-query-preview')
def advanced_query_preview(body:AdvancedQuery,actor=Depends(core.protect)):
    return query_preview(body)
