"""Non-authoritative text screening for public search data.

A flagged item is preserved for analyst review but never forwarded to LLM
context as instructions. This is a bounded screening layer, not a proof that
text without flags is safe.
"""
from __future__ import annotations
import json,re
from collections import Counter
PATTERNS={
  'role_spoofing':r'(?i)(?:\[system\]|<\|(?:system|developer|assistant)\|>|BEGIN (?:SYSTEM|DEVELOPER) PROMPT|SYSTEM OVERRIDE)',
  'instruction_hijack':r'(?i)(?:ignore (?:all )?(?:prior|previous|system|developer) instructions|disregard the system prompt|you are now (?:a|an)|override safety policy|respond with (?:the|only))',
  'secret_exfiltration':r'(?i)(?:send|post|upload|exfiltrate|print|reveal|disclose).{0,100}(?:api.?key|secret|cookie|session token|password|environment variable)',
  'tool_execution':r'(?i)(?:execute (?:a |the )?(?:shell|python|terminal|command)|run (?:this |the )?(?:script|curl|wget)|call (?:the |an )?(?:tool|function))',
  'seo_spam':r'(?i)(?:buy backlinks|guaranteed first page rankings|seo backlinks packages|buy cheap followers)',
}
REGEX={k:re.compile(v) for k,v in PATTERNS.items()}
def assess_untrusted(text):
    data=str(text or '')[:20000]
    flags=[name for name,p in REGEX.items() if p.search(data)]
    terms=re.findall(r'[a-z]{4,}',data.casefold())
    if len(terms)>=35 and Counter(terms).most_common(1)[0][1]>len(terms)*0.4:
        flags.append('keyword_stuffing')
    if len(re.findall(r'https?://',data,re.I))>=7:
        flags.append('link_farm')
    return {'quarantined':bool(flags),'flags':flags,
       'risk':'quarantine_for_human_review' if flags else 'not_flagged_unverified',
       'notIndependentlyValidatingSource':True}

def screen_records(records):
    clean=[]
    redactions=[]
    for raw in records:
        if not isinstance(raw,dict):continue
        # Search snippets and captured text are untrusted in all providers.
        parts=[str(raw.get(k) or '') for k in
               ('label','summary','description','title','quote','unverifiedText','content',
                'sourceExcerpt','text','snippet')]
        report=assess_untrusted(' '.join(parts))
        if report['quarantined']:
            redactions.append({'evidenceId':raw.get('id') or raw.get('evidenceId'),
                               'flags':report['flags']})
            # Preserve source metadata and quoted provenance, NOT attacker text.
            protected=dict(raw)
            for field in ('summary','description','title','label','quote','unverifiedText',
                          'content','sourceExcerpt','text','snippet'):
                if field in protected:protected[field]='[Untrusted source text withheld for human review]'
            protected['sourceSafetyFlags']=report['flags']
            clean.append(protected)
        else:clean.append(raw)
    return clean,redactions

def sanitize_context(context):
    """All AI-fed source arrays are sanitized; person partitions included."""
    src=dict(context)
    redactions=[]
    for key in ('evidence','untrustedCapturedSourceText','freshUnverifiedBraveContext'):
        if isinstance(src.get(key),list):
            src[key],flags=screen_records(src[key])
            redactions.extend(flags)
    partitions=src.get('candidateEvidencePartitions')
    if isinstance(partitions,dict):
        # Candidate partition formats differ; recursive traversal redacts source leaves.
        src['candidateEvidencePartitions']=sanitize_nested(partitions,redactions)
    elif isinstance(partitions,list):
        src['candidateEvidencePartitions']=sanitize_nested(partitions,redactions)
    return src,redactions

def sanitize_nested(obj,redactions):
    if isinstance(obj,list):
        return [sanitize_nested(x,redactions) for x in obj]
    if isinstance(obj,dict):
        row=dict(obj)
        source_fields=('summary','description','title','label','quote','unverifiedText','sourceExcerpt','snippet')
        if any(k in row for k in source_fields):
            check=assess_untrusted(' '.join(str(row.get(k) or '') for k in source_fields))
            if check['quarantined']:
                redactions.append({'evidenceId':row.get('id') or row.get('evidenceId'),
                                   'flags':check['flags']})
                for k in source_fields:
                    if k in row:row[k]='[Untrusted source text withheld for human review]'
        return {k:sanitize_nested(v,redactions) for k,v in row.items()}
    return obj
