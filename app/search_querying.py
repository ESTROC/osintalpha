"""Question-led public-search expansion without hardcoded people or employers.

A parsed person-name is an unverified search label, never an identified
individual. Queries prioritize a diverse set of publisher URLs, not contact
harvesting or uncontrolled scraping.
"""
from __future__ import annotations
import re
from .query_parse import parse_question

_PERSON_ANCHORS=(
 r'\b(?:a\s+)?person\s+(?:called(?:\s+as)?|named)\s+',
 r'\b(?:individual|someone)\s+(?:called|named)\s+',
)
_STOP_BOUNDARY=r'(?:who|whose|has|had|is|was|worked|working|studied|graduate(?:d)?|passed|from|at|in|with|and|that)\b'
_WORDBOUND=re.compile(r"[A-Za-z][A-Za-z'.-]{1,42}")
_UNHELPFUL={
 'want','know','please','person','someone','individual','called','named','about',
 'find','more','details','information','worked','working','has','have','had','was',
 'with','from','passed','out','form','the','their','there','where','who','which',
 'that','and','is','as','at','in','for','graduated','graduation','education',
 'record','records','source','sources','public','profile','university','college',
 'engineering','engineer','academic','professional','profession','of'
}
_TOPIC_GROUPS=[
 ('cyber','security','infosec'),('software','development','coding','developer'),
 ('internship','intern','experience'),('engineering','engineer'),
 ('education','college','school','university','graduation')]
_CONTACT_HOSTS={'rocketreach.co','signalhire.com','lusha.com'}

def person_name(question):
    original=' '.join(str(question or '').split())
    # A sentence can explicitly introduce a person after filler words.
    for prefix in _PERSON_ANCHORS:
        pat=re.compile(prefix+r'(?P<name>[A-Za-z][A-Za-z\'.-]*(?:\s+[A-Za-z][A-Za-z\'.-]*){1,3}?)'
             +r'(?=\s+'+_STOP_BOUNDARY+r'|[,.;?!]|$)',re.I)
        match=pat.search(original)
        if match:
            name=match.group('name').strip()
            if len(name.split())>=2:
                return name
    parsed=parse_question(original)
    name=parsed.subject_text
    if 2<=len(name.split())<=4 and len(name)<135:
        return name
    return ''

def question_clues(question,name,context=None):
    original=' '.join(str(question or '').split())
    remainder=original
    if name:
        remainder=re.sub(re.escape(name),' ',remainder,flags=re.I,count=1)
    words=re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}",remainder)
    keywords=[]
    for word in words:
        low=word.casefold()
        if low in _UNHELPFUL or low in {x.casefold() for x in name.split()}:
            continue
        if low not in {x.casefold() for x in keywords}:
            keywords.append(word)
    hints=context or {}
    if hints.get('organization'):
        keywords.insert(0,str(hints['organization']).strip())
    if hints.get('city'):
        keywords.append(str(hints['city']).strip())
    # Literal public clues, no profession/employer inference.
    return keywords[:12]

def select_queries(question,subject,context=None,lens='general',depth=4):
    """Return <=depth diverse query variants; first preserves analyst wording."""
    original=' '.join(str(question or '').split())[:200]
    if not original:
        return []
    name=person_name(original) or person_name(subject)
    if not name:
        return [original]
    keys=question_clues(original,name,context)
    compact=[str(x).strip() for x in keys if str(x).strip()]
    parsed=parse_question(original)
    # These are literal phrases from the question, never verified employers.
    organizations=list(parsed.organization_clues)
    entered=str((context or {}).get('organization') or '').strip()
    if entered and entered.casefold() not in {x.casefold() for x in organizations}:
        organizations.insert(0,entered)
    primary=organizations[0] if organizations else ''
    secondary_match=re.search(
        r'\b(?:graduated\s+from|passed\s+out\s+from|educated\s+at|studied\s+at|from)\s+'
        r'([A-Za-z][A-Za-z0-9_.-]{2,50})(?=\b|$)',original,re.I)
    secondary=secondary_match.group(1) if secondary_match else ''
    if secondary.casefold() in {'the','a','an','work','job','home','here'}:
        secondary=''
    label='"'+name.replace('"','')+'"'
    out=[original]
    if primary:
        out.append(f'{label} "{primary}"'+(' '+compact[0] if compact else ''))
    elif compact:
        out.append(f'{label} "'+compact[0]+'"')
    else:
        out.append(label)
    # Public posts are often indexed even when LinkedIn /in/ profiles are not.
    if lens in ('general','professional','education'):
        out.append(f'site:linkedin.com/posts/ {label}'+
                   (' "'+primary+'"' if primary else (' '+compact[0] if compact else '')))
    if secondary and secondary.casefold() not in (primary.casefold(),name.casefold()):
        out.append(f'{label} "{secondary}"')
    elif lens=='professional':
        out.append(f'site:linkedin.com/in/ {label}'+
                   (' "'+primary+'"' if primary else ''))
    if len(out)<depth:
        for hint in compact:
            q=f'{label} "{hint}"'
            if q not in out:
                out.append(q)
            if len(out)>=depth:break
    seen=set();dedup=[]
    for item in out:
        item=' '.join(item.split())[:200]
        key=item.casefold()
        if key not in seen:
            seen.add(key);dedup.append(item)
        if len(dedup)>=depth:break
    return dedup

def contact_directory(url):
    from urllib.parse import urlparse
    hostname=(urlparse(str(url or '')).hostname or '').lower()
    return any(hostname==host or hostname.endswith('.'+host) for host in _CONTACT_HOSTS)
