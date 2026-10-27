"""Conservative evidence gates; never infer person identity from name hits.

"Supported by an observed passage" means an excerpt contains the exact quote.
It does *not* mean the statement is true, the publisher owns the page, or
the account/profile belongs to the case's subject.
"""
from __future__ import annotations
from collections import Counter
from urllib.parse import urlparse
import re

STOP={'which','where','when','what','about','this','that','find','search','profile',
      'evidence','public','person','review','source','sources','verify','their',
      'from','with','and','the','who','was','are','has','does','for','can','how'}

def tokens(value):
    return set(re.findall(r'[\w-]{3,}',str(value or '').casefold()))-STOP

def source_fitness(row,question,subject='',context=None):
    """Explainable question fit. Result is a ranking score, not a probability."""
    if row.get('status')=='rejected':
        return {'score':0,'usable':False,'reason':'rejected_source'}
    src=' '.join((str(row.get(k) or '') for k in ('label','summary','source_url')))
    q=tokens(question); text=tokens(src)
    intersection=q&text
    subject_tokens=tokens(subject)
    subject_overlap=subject_tokens&text
    if not intersection and not subject_overlap:
        return {'score':0,'usable':False,'reason':'irrelevant_to_question'}
    neg=[]
    for field in ('city','organization','public_handle'):
        clue=str((context or {}).get(field) or '').strip()
        if not clue:continue
        try:
            import json
            raw=row.get('raw_json') or {}
            raw=json.loads(raw) if isinstance(raw,str) else raw
            raw=raw if isinstance(raw,dict) else {}
        except (ValueError,TypeError):
            raw={}
        value={'city':raw.get('location') or raw.get('city'),
               'organization':raw.get('company') or raw.get('organization'),
               'public_handle':raw.get('login') or raw.get('username') or raw.get('handle')}.get(field)
        if value and str(value).strip().casefold()!=clue.casefold():
            neg.append(field)
    score=2*len(intersection)+len(subject_overlap)-4*len(neg)
    return {'score':max(0,score),'usable':score>0 and not neg,
            'reason':'candidate_with_conflicting_public_clues' if neg else
                     'question_overlap_only' if score>0 else 'not_relevant',
            'matchedTerms':sorted(intersection)[:12],
            'conflictingClues':neg}

def evidence_coverage(rows,question,subject='',context=None):
    graded=[(r,source_fitness(r,question,subject,context)) for r in rows]
    usable=[(r,x) for r,x in graded if x['usable']]
    domains={urlparse(str(r.get('source_url') or '')).hostname for r,x in usable
             if str(r.get('source_url') or '').startswith('https://')}
    return {'candidateRecords':len(rows),'questionRelevant':len(usable),
            'independentPublisherHosts':len(domains),
            'unreliableOrIrrelevant':len(rows)-len(usable),
            'onlyNameOverlap':len(usable)>0 and len(tokens(question))<=len(tokens(subject)),
            'verifiedPersonIdentity':False,
            'limitation':'Token/relevance evidence is not an independently verified identity or fact.'}

def source_quote_match(quote, captured_text):
    """Require a substantial literal passage, not hallucinated paraphrase."""
    phrase=' '.join(str(quote or '').split())
    content=' '.join(str(captured_text or '').split())
    if not 15<=len(phrase)<=900 or not content:
        return False
    return phrase.casefold() in content.casefold()

def identity_review_gate(subject_type,rows,question,subject='',context=None):
    coverage=evidence_coverage(rows,question,subject,context)
    if subject_type!='person':
        return {'needsHumanIdentityReview':False,'identityVerified':False,
                'coverage':coverage,'reason':'not_person_identification'}
    return {'needsHumanIdentityReview':True,'identityVerified':False,
            'coverage':coverage,
            'reason':'profile_name_or_indexed_hit_never_confirms_person' if coverage['questionRelevant'] else 'no_relevant_candidate_record',
            'requires':'Human review of independently corroborated original identity evidence, including negative namesakes.'}

def guard_synthesis(answer,question,subject_type,rows,subject='',context=None,
                    *,has_fresh_context=False,has_verified_quote=False,
                    needs_disambiguation=False):
    """Fail closed on unsupported definitive person biographies.

    The returned action is visible to callers. Empty evidence cannot establish
    a person fact; relevant snippet links can be discussed only as candidates.
    """
    gate=identity_review_gate(subject_type,rows,question,subject,context)
    cover=gate['coverage']
    if needs_disambiguation:
        return {'action':'clarify','answer':answer,'gate':gate}
    no_usable=cover['questionRelevant']==0 and not has_fresh_context and not has_verified_quote
    if no_usable:
        return {'action':'abstain','answer':'Insufficient attributable evidence to answer this question. No verified conclusion about the subject is available. Source absence is not evidence of absence. Please supply a distinguishing public source or identifier.','gate':gate}
    if subject_type=='person' and not has_verified_quote:
        return {'action':'candidate_only','answer':'Public-source candidates were found, but the intended person is not independently identified. Review the original sources and distinguish namesakes before stating a biography, employer or allegation.','gate':gate}
    # A text quote is only proof of text presence, never proof of account ownership.
    return {'action':'bounded_unverified','answer':answer,'gate':gate}
