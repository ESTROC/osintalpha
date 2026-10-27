"""P1 029–038: explicit question taxonomy, source utility and uncertainty.

A routing decision selects permitted APIs; it is NOT a confirmed person, job,
jurisdiction, record completeness, or ground-truth source reliability.
"""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse
from collections import defaultdict
import re
from .query_parse import parse_question

TASK_PATTERNS={
    'passive_technical':r'\b(dns|domain|ip address|passive scan|certificate transparency|whois)\b',
    'public_security':r'\b(cve|vulnerability|advisory|cybersecurity|infosec|malware|security research)\b',
    'academic':r'\b(research paper|publication|orcid|researcher|professor|scholar|academic|scientific)\b',
    'business':r'\b(plumb(?:er|ing)|electrician|repair|trade|contractor|business listing|shop|local service|restaurant)\b',
    'legal_entity':r'\b(registration|incorporated|company number|llp|pvt|private limited|annual report|legal entity)\b',
    'education':r'\b(student|school|college|university|scholarship|competition|campus|exam)\b',
    'public_event':r'\b(event|festival|public meeting|conference|sports match|ceremony|workshop|public notice)\b',
    'professional':r'\b(github|software engineer|developer|portfolio|employment|cv|linkedin|work history)\b'
}
PRIORITY=['passive_technical','public_security','academic','business','legal_entity','education','public_event','professional']

# Explicit source utility rubric, not an ML-learnt performance claim. Providers
# are filtered a second time through the live connector catalog/scope.
UTILITY={
  'public_security':['github','gdelt'],
  'academic':['openalex','crossref'],
  'business':[],
  'legal_entity':['gleif','gdelt','wikidata'],
  'education':['gdelt','wikipedia'],
  'public_event':['gdelt','wikipedia'],
  'professional':['github','stackoverflow','gdelt'],
  'passive_technical':['dns','internetdb'],
  'general_person':['gdelt','wikipedia'],
  'general_organization':['gleif','gdelt','wikidata'],
}
LENSES={'public_security':'general','academic':'education','business':'trade',
        'legal_entity':'organization','education':'education',
        'public_event':'general','professional':'professional',
        'general_person':'general','general_organization':'organization'}

def question_type(question,subject_type='person'):
    text=' '.join(str(question or '').casefold().split())
    if subject_type in ('domain','ip'): return 'passive_technical'
    ranked=[(t,len(re.findall(pattern,text))) for t,pattern in TASK_PATTERNS.items()]
    candidates=[(t,n) for t,n in ranked if n]
    if candidates:
        candidates.sort(key=lambda x:(-x[1],PRIORITY.index(x[0])))
        return candidates[0][0]
    return 'general_organization' if subject_type=='organization' else 'general_person'

def permitted_sources(kind,task,catalog):
    scoped={x.id for x in catalog if kind in x.scope}
    choices=[p for p in UTILITY.get(task,[]) if p in scoped]
    if task=='passive_technical':
        choices=['internetdb' if kind=='ip' else 'dns'] if kind in ('ip','domain') else []
    return choices[:3]

def plan_question(question,kind,catalog):
    parsed=parse_question(question)
    task=question_type(question,kind)
    providers=permitted_sources(kind,task,catalog)
    return {
      'questionType':task,
      'searchLens':LENSES.get(task,'general'),
      'providers':providers,
      'parsed':parsed.as_dict(),
      'needsClarification':bool(kind=='person' and parsed.identity_state=='given_name_only'),
      'clarification':'Add a full public name or a distinguishing public handle, workplace or city.' if kind=='person' and parsed.identity_state=='given_name_only' else '',
      'sourcePolicy':'explicit_task_to_connector_utility; not experimentally calibrated',
      'originalQuery':parsed.original,
      'variants':list(parsed.query_variants[:4])
    }

# Group publisher site hosts. This is not proven independent ownership;
# different hosts operated by one organization may still correlate.
TWO_PART_TLDS={'co.uk','org.uk','gov.uk','ac.uk','co.in','org.in','gov.in','com.au','co.nz'}
def publisher_group(url):
    try:
        host=(urlparse(str(url)).hostname or '').casefold().strip('.')
    except ValueError:
        return ''
    if not host:return ''
    bits=host.split('.')
    if len(bits)<=2:return host
    suffix='.'.join(bits[-2:])
    return '.'.join(bits[-3:]) if suffix in TWO_PART_TLDS and len(bits)>=3 else suffix

def balance_results(items,max_per_site=2,limit=20):
    """Return candidate URL diversity, not independent source corroboration."""
    if not 1<=max_per_site<=8 or not 1<=limit<=100:
        raise ValueError('bounded counts required')
    used=defaultdict(int);seen=set();output=[]
    for item in items:
        if not isinstance(item,dict):continue
        url=str(item.get('url') or '')
        if not url.startswith('https://') or url in seen:continue
        group=publisher_group(url)
        if not group or used[group]>=max_per_site:continue
        seen.add(url);used[group]+=1
        output.append(item)
        if len(output)>=limit:break
    return output

def coverage_decision(items,queries_executed=0,provider_error=False,
                      *,min_sources=5,min_sites=3,max_queries=3):
    """Bounded paging. Empty results and publisher diversity are diagnostic."""
    good=balance_results(items,max_per_site=2,limit=100)
    sites={publisher_group(r['url']) for r in good}
    adequate=len(good)>=min_sources and len(sites)>=min_sites
    if provider_error:return {'stop':True,'reason':'upstream_error','sources':len(good),'sites':len(sites)}
    if adequate:return {'stop':True,'reason':'candidate_diversity_target_met_not_exhaustive','sources':len(good),'sites':len(sites)}
    if queries_executed>=max_queries:return {'stop':True,'reason':'query_budget_exhausted','sources':len(good),'sites':len(sites)}
    return {'stop':False,'reason':'need_additional_index_page','sources':len(good),'sites':len(sites)}
