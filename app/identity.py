"""Explicit public-attribute identity comparisons; no silent identity merges.

The engine documents matches and differences in recorded public metadata.
It deliberately does not output verified identity or a fake confidence score.
Names alone never establish account ownership or person identity.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException,Query
from . import db
from . import main as core

router=APIRouter()

def normalize(value):
    return ' '.join(re.findall(r'[a-z0-9]+',str(value or '').casefold()))

def clean(value,limit=180):
    if isinstance(value,str):return ' '.join(value.strip().split())[:limit]
    return ''

def attributes(record):
    try:raw=json.loads(record.get('raw_json') or '{}')
    except (ValueError,TypeError):raw={}
    if not isinstance(raw,dict):raw={}
    source=str(record.get('provider') or '')
    # Authors on publication titles are not automatically profile owners.
    profile=source in {'github','stackoverflow','openalex','analyst'}
    name=clean(raw.get('display_name') or raw.get('name') or (record['label'] if profile else ''))
    institution=raw.get('institutions') or []
    if not isinstance(institution,list):institution=[]
    company=clean(raw.get('company') or raw.get('organization') or (institution[0] if institution else ''))
    location=clean(raw.get('location') or raw.get('city') or '')
    handle=clean(raw.get('login') or raw.get('username') or raw.get('handle') or '')
    website=clean(raw.get('website_url') or raw.get('blog') or '')
    if website.startswith(('http://','https://')):
        website=website.split('://',1)[1].lower().rstrip('/')
    else:website=''
    return {'recordId':record['id'],'provider':source,
       'label':clean(record['label'],220),'url':record['source_url'],
       'reviewStatus':record['status'],'name':name,'organization':company,
       'location':location,'publicHandle':handle,'website':website,
       'note':'Only explicit public metadata is shown; this does not verify identity.'}

def compare(left,right):
    equal=[];difference=[];unknown=[]
    weights={'name':0,'organization':2,'location':1,'publicHandle':3,'website':4}
    for field in weights:
        a=left[field];b=right[field]
        if not a or not b:unknown.append(field);continue
        if normalize(a)==normalize(b):
            equal.append({'field':field,'value':a})
        else:
            difference.append({'field':field,'left':a,'right':b,
                 'meaning':'Different published attributes, not proof of different individuals.'})
    # A shared display name or workplace/location alone is NOT a proposed merge.
    identifiers=[x['field'] for x in equal if x['field'] in ('publicHandle','website')]
    strength=('investigate_public_identifier' if identifiers else
              'contextual_similarity_only' if any(x['field'] in ('organization','location') for x in equal)
              else 'no_link_signal')
    return {'left':left,'right':right,'matching':equal,'differing':difference,
       'missing':unknown,'signalLevel':strength,'identityVerified':False,
       'requiresHumanReview':True,
       'limitation':'Matching usernames or websites across platforms is not sufficient to establish same-person ownership. Differences may reflect changes over time.'}

def rank_against_clues(row,context):
    matched=[];unknown=[];different=[]
    for field,context_key in [('location','city'),('organization','organization'),('publicHandle','public_handle')]:
        expected=clean(context.get(context_key) or '')
        if not expected:continue
        found=clean(row.get(field))
        if not found:unknown.append(field)
        elif normalize(expected)==normalize(found) or normalize(expected) in normalize(found):
            matched.append(field)
        else:different.append({'field':field,'published':found,'clue':expected})
    return {'matched':matched,'unknown':unknown,'different':different,
       'publicClueMatches':len(matched),
       'note':'Unknown fields are not contradictions. Different metadata may reflect another person, outdated information or a relocation.'}

@router.get('/api/cases/{case_id}/identity-analysis')
def identity_analysis(case_id:str,
     left:str=Query(default='',max_length=90),
     right:str=Query(default='',max_length=90),
     actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        c=conn.execute('SELECT city,organization,profession,public_handle FROM case_context WHERE case_id=?',(case_id,)).fetchone()
        context=dict(c) if c else {}
        rows=[dict(r) for r in conn.execute('''SELECT id,provider,label,summary,source_url,raw_json,status
             FROM evidence WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT 2000''',(case_id,))]
    profile=[attributes(x) for x in rows if x['provider'] not in ('crossref','gdelt','dns','internetdb')]
    annotated=[dict(p,clues=rank_against_clues(p,context)) for p in profile]
    annotated.sort(key=lambda p:(-p['clues']['publicClueMatches'],p['provider'],p['label']))
    byid={p['recordId']:p for p in annotated}
    if (left and not right) or (right and not left):
        raise HTTPException(422,'Two source record IDs are required for comparison.')
    result=None
    if left and right:
        if left==right:raise HTTPException(422,'Choose two different source records.')
        if left not in byid or right not in byid:
            raise HTTPException(404,'One or both source records are not accessible in this case.')
        result=compare(byid[left],byid[right])
    suggestions=[]
    # Suggestions have a strict bound; no automatic identity grouping or scoring.
    possible=annotated[:100]
    for n,a in enumerate(possible):
        if a['reviewStatus']=='rejected':continue
        for b in possible[n+1:]:
            if a['provider']==b['provider'] or b['reviewStatus']=='rejected':continue
            comparison=compare(a,b)
            if comparison['signalLevel']!='investigate_public_identifier':continue
            suggestions.append({'leftId':a['recordId'],'rightId':b['recordId'],
                 'leftLabel':a['label'],'rightLabel':b['label'],
                 'providers':[a['provider'],b['provider']],
                 'matching':comparison['matching'],
                 'differing':comparison['differing'],
                 'identityVerified':False})
            if len(suggestions)>=40:break
        if len(suggestions)>=40:break
    return {'records':annotated[:120],'totalSourceRecords':len(rows),
        'totalProfileCandidates':len(profile),'pairSuggestions':suggestions,
        'comparison':result,'context':context,
        'notice':'No automatic identity merge or probability is asserted. Identity comparisons require source-specific corroboration and analyst review.'}
