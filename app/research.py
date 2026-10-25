"""Bounded public-source search planning; no unsupported identity merges.

Plans are transparent and deterministic. Upstream APIs are contacted only through
the allowlisted connector catalogue. Analyst-supplied identity clues affect
additional source queries; they are NOT claims about the person.
"""
from __future__ import annotations
from dataclasses import dataclass
from .connectors import CATALOG

@dataclass(frozen=True)
class QueryStep:
    provider:str
    query:str
    reason:str

def clean(value,maxlen=90):
    return ' '.join(str(value or '').strip().split())[:maxlen]

def plan(case,context=None,depth='standard',providers=None):
    context=context or {}
    kind=case['subject_type']
    name=clean(case['query'],160)
    available={c.id for c in CATALOG if kind in c.scope}
    desired=[p for p in (providers or sorted(available)) if p in available]
    city=clean(context.get('city'))
    org=clean(context.get('organization'))
    handle=clean(context.get('public_handle')).lstrip('@')
    profession=clean(context.get('profession')).casefold()
    # Prioritize the source category relevant to the task.
    if kind=='person':
        if any(term in profession for term in ('university','academic','research','scientist','professor')):
            priority=['openalex','crossref','github','stackoverflow','gdelt','wikipedia','wikidata']
        else:
            priority=['github','stackoverflow','gdelt','wikipedia','wikidata','openalex','crossref']
    elif kind=='organization':
        priority=['gleif','gdelt','github','wikipedia','wikidata']
    else:
        priority=['dns','internetdb']
    desired.sort(key=lambda p:(priority.index(p) if p in priority else 50,p))
    if depth=='quick':desired=desired[:3]
    steps=[QueryStep(p,name,'Original subject query') for p in desired]
    # New queries are context-aware without modifying the subject's canonical identity.
    if kind=='person':
        if handle and 'github' in desired and handle.casefold()!=name.casefold():
            steps.append(QueryStep('github',handle,'Known public handle candidate'))
        if org and 'gdelt' in desired:
            steps.append(QueryStep('gdelt',name+' '+org,'Subject and known organization'))
        if city and not org and 'gdelt' in desired:
            steps.append(QueryStep('gdelt',name+' '+city,'Subject and known city'))
        if org and 'wikipedia' in desired:
            steps.append(QueryStep('wikipedia',name+' '+org,'Subject and organization'))
    elif kind=='organization':
        if city and 'gdelt' in desired:
            steps.append(QueryStep('gdelt',name+' '+city,'Organization and region'))
    # Avoid redundant API calls, never exceed 12 requests.
    dedup=set()
    result=[]
    for step in steps:
        key=(step.provider,step.query.casefold())
        if key not in dedup:
            dedup.add(key)
            result.append(step)
    return result[:(12 if depth=='thorough' else 9)]
