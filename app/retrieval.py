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

def rank_case_evidence(rows,question,context=None,limit=35,*,focused_person=False,subject=''):
    """Return relevant diverse records; no match score is a probability."""
    ctx=context or {}
    qtokens=words(question)
    hint_tokens=words(' '.join(str(ctx.get(k,'') or '') for k in
         ('city','organization','profession','public_handle')))
    q=Counter(qtokens)
    hints=Counter(hint_tokens)
    provider_docs=defaultdict(int)
    scored=[]
    for item in rows:
        try:raw=json.loads(item.get('raw_json') or '{}')
        except (ValueError,TypeError):raw={}
        label=Counter(words(item.get('label','')))
        summary=Counter(words(item.get('summary','')))
        attrs=Counter(words(' '.join(str(raw.get(k) or '') for k in
          ('login','username','handle','company','location','bio','institution','organization'))))
        common=sum(min(1,label[t])*6+min(1,summary[t])*2+min(1,attrs[t])*4 for t in q)
        hintmatch=sum((min(1,attrs[t])*3+min(1,summary[t])) for t in hints)
        review=1.0 if item.get('status')=='corroborated' else (-2 if item.get('status')=='rejected' else 0)
        score=common+hintmatch+review
        scored.append((score,item))
    # Candidate retrieval must distinguish evidence about the requested
    # person/topic from unrelated same-name directory/profile records.
    excluded_as_namesake=0
    if focused_person:
        from .search_querying import person_name, question_clues
        name=person_name(question) or person_name(subject)
        qclues=question_clues(question,name,ctx)
        identity_terms=set(words(name))
        meaningful=set(words(' '.join(qclues)))-identity_terms
        # Org names and education identifiers are high-signal, relative to
        # broad technology topics that many unrelated people can share.
        from .query_parse import parse_question
        parsed=parse_question(question)
        strong=set(words(' '.join(parsed.organization_clues)))
        education=re.search(
            r'\b(?:graduated\s+from|passed\s+out\s+from|educated\s+at|studied\s+at|from)\s+'
            r'([A-Za-z][A-Za-z0-9_.-]{2,50})\b',question,re.I)
        if education:strong|=set(words(education.group(1)))
        strong-=identity_terms
        filtered=[]
        for score,row in scored:
            raw=row.get('raw_json') or '{}'
            try:parsed_raw=json.loads(raw) if isinstance(raw,str) else raw
            except (ValueError,TypeError):parsed_raw={}
            if not isinstance(parsed_raw,dict):parsed_raw={}
            text=' '.join(str(row.get(x) or '') for x in ('label','summary'))
            text+=' '+' '.join(str(parsed_raw.get(x) or '') for x in
                 ('bio','company','institution','organization','description','snippet','location'))
            normalized=' '.join(text.casefold().split())
            body_words=set(words(normalized))
            name_match=not name or ' '.join(name.casefold().split()) in normalized
            clue_match=bool((strong or meaningful)&body_words)
            if name_match and (not meaningful or clue_match):
                if strong and not (strong&body_words):
                    excluded_as_namesake+=1
                    continue
                filtered.append((score+len((strong or meaningful)&body_words)*5,row))
            else:
                excluded_as_namesake+=1
        scored=filtered
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
         'method':'lexical query+public clue ranking; no calibrated identity confidence',
         'providers':dict(Counter(r.get('provider','unknown') for r in selected)),
          'candidateFilter':('question_clue_overlap' if focused_person else 'lexical'),
          'excludedAsUnrelatedCandidates':excluded_as_namesake,
          'identitiesVerified':0}
