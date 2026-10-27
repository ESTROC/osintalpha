"""Explainable lexical retrieval over every saved source record.

This is deliberately not presented as semantic identity resolution.
It improves AI context selection from the whole case without auto-merging people.
"""
from __future__ import annotations
import json
import math
import re
from collections import Counter, defaultdict

STOP={'a','an','and','are','as','at','be','by','can','for','from','has','have','how',
      'i','in','is','it','me','of','on','or','our','the','their','there','this','to',
      'was','were','what','when','where','which','who','why','with','you','your',
      'please','find','research','tell','about','person','profile','evidence'}

def words(value):
    return [x for x in re.findall(r'[a-z0-9_]{2,}',str(value or '').casefold())
            if x not in STOP]

def _conflicting_public_clues(raw,context):
    """Explicit publisher metadata only: missing fields are not contradictions."""
    negative=[]
    if not isinstance(raw,dict):return negative
    expected={
        'city':('city','location'),
        'organization':('organization','company','employer'),
        'public_handle':('public_handle','handle','username','login'),
    }
    for label,keys in expected.items():
        goal=str((context or {}).get(label) or '').strip().casefold()
        if not goal:continue
        value=next((str(raw.get(k) or '').strip().casefold() for k in keys
                    if str(raw.get(k) or '').strip()),'')
        if value and value!=goal:negative.append(label)
    return negative

def rank_case_evidence(rows,question,context=None,limit=35):
    """Return relevant diverse records; no match score is a probability."""
    ctx=context or {}
    qtokens=words(question)
    hint_tokens=words(' '.join(str(ctx.get(k,'') or '') for k in
         ('city','organization','profession','public_handle')))
    q=Counter(qtokens)
    hints=Counter(hint_tokens)
    provider_docs=defaultdict(int)
    scored=[]
    excluded={'rejected':0,'conflicting_public_metadata':0}
    for item in rows:
        if item.get('status')=='rejected':
            excluded['rejected']+=1
            continue
        try:raw=json.loads(item.get('raw_json') or '{}')
        except (ValueError,TypeError):raw={}
        if not isinstance(raw,dict):raw={}
        conflicts=_conflicting_public_clues(raw,ctx)
        if conflicts:
            excluded['conflicting_public_metadata']+=1
            continue
        label=Counter(words(item.get('label','')))
        summary=Counter(words(item.get('summary','')))
        attrs=Counter(words(' '.join(str(raw.get(k) or '') for k in
          ('login','username','handle','company','location','bio','institution','organization'))))
        common=sum(min(1,label[t])*6+min(1,summary[t])*2+min(1,attrs[t])*4 for t in q)
        hintmatch=sum((min(1,attrs[t])*3+min(1,summary[t])) for t in hints)
        review=1.0 if item.get('status')=='corroborated' else (-2 if item.get('status')=='rejected' else 0)
        score=common+hintmatch+review
        scored.append((score,item))
    scored.sort(key=lambda x:(-x[0],x[1].get('provider',''),x[1].get('id','')))
    selected=[]
    for score,row in scored:
        source=row.get('provider','unknown')
        if provider_docs[source]>=14 and len(selected)<limit:
            continue
        selected.append(row)
        provider_docs[source]+=1
        if len(selected)==limit:break
    if len(selected)<limit:
        included={r.get('id') for r in selected}
        for score,row in scored:
            if row.get('id') not in included:
                selected.append(row)
                if len(selected)==limit:break
    return selected,{'totalRecords':len(rows),'selected':len(selected),
         'method':'lexical ranking with explicit public-metadata contradiction exclusions; no calibrated identity confidence',
         'excludedByReason':excluded,
         'providers':dict(Counter(r.get('provider','unknown') for r in selected))}
