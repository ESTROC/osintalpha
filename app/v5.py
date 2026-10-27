"""V5 external search and reviewable source-text capture.

Search results are attributed *candidates*, not verified facts. Page capture is
limited to predefined public hosts: arbitrary analyst URLs are never fetched.
"""
from __future__ import annotations
import hashlib
import html
import ipaddress
import json
import os
import re
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urlsplit
import httpx
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import main as core
from . import db
from .lineage import save_observation
from .search_policy import balance_results, coverage_decision

router=APIRouter()
TRUSTED_EXACT={'github.com','www.github.com','stackoverflow.com','www.stackoverflow.com',
'doi.org','www.doi.org','openalex.org','www.openalex.org','www.wikidata.org',
'www.gleif.org','www.crossref.org','crossref.org','en.wikipedia.org'}
TRUSTED_SUFFIX=('.wikipedia.org','.wikidata.org')
MAX_DOWNLOAD=180_000
MAX_TEXT=35_000

def public_https(raw):
    try:
        p=urlsplit(str(raw))
        host=(p.hostname or '').lower().rstrip('.')
        if p.scheme!='https' or not host or p.username or p.password or p.port not in (None,443):
            return False
        if any(ch.isspace() for ch in raw) or len(raw)>600:return False
        if host=='localhost' or host.endswith(('.local','.internal','.test','.invalid','.example')):return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:pass
        return '.' in host
    except (ValueError,TypeError):
        return False

def capture_allowed(raw):
    if not public_https(raw):return False
    host=urlsplit(raw).hostname.lower().rstrip('.')
    return host in TRUSTED_EXACT or any(host.endswith(end) for end in TRUSTED_SUFFIX)

class TextExtract(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0
        self.bits=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','noscript','svg','iframe','head'):
            self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg','iframe','head'):
            self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():
            self.bits.append(data.strip())
    def result(self):
        return re.sub(r'\s+',' ',' '.join(self.bits)).strip()[:MAX_TEXT]

def extract_text(content,ctype):
    data=content.decode('utf-8',errors='replace')
    if 'html' not in ctype:
        return re.sub(r'\s+',' ',data).strip()[:MAX_TEXT]
    parser=TextExtract()
    parser.feed(data)
    return parser.result()

@router.get('/api/research/providers')
def providers(actor=Depends(core.actor_from_cookie)):
    return {'web':{'name':'Brave Web Search','configured':bool(os.getenv('BRAVE_SEARCH_API_KEY','').strip()),
                   'note':'Optional third-party index. URLs and snippets are not proof of identity or contents.'},
            'capture':{'hostLimited':True,'allowedHosts':sorted(TRUSTED_EXACT),
                       'limitBytes':MAX_DOWNLOAD,'notice':'Source capture is text extraction, not a forensic archive.'}}

class WebSearchInput(BaseModel):
    query:str|None=Field(default=None,max_length=200)
    depth:int=Field(default=2,ge=1,le=4)
    pages:int=Field(default=1,ge=1,le=3)
    adaptive:bool=False
    lens:Literal['general','professional','education','trade','organization']='general'
    freshness:Literal['all','pd','pw','pm','py']='all'
    country:Literal['US','IN','GB','CA','AU','DE','FR']='US'
    search_lang:Literal['en','hi','bn','ta','te','mr','de','fr']='en'
    consent:bool=False

def make_queries(case,context,body,original_question=''):
    """Use a small, explainable profile-oriented query budget.

    Site filters improve discovery coverage, not identity certainty. We never
    claim that a LinkedIn search snippet is the underlying LinkedIn profile.
    """
    base=' '.join((body.query or original_question or case['query']).strip().split())
    if not base:raise HTTPException(422,'Enter a public-source research query')
    org=' '.join(str(context.get('organization') or '').split())[:90]
    city=' '.join(str(context.get('city') or '').split())[:70]
    handle=' '.join(str(context.get('public_handle') or '').split())[:65].lstrip('@')
    distinct=[clue for clue in (org,city) if clue and clue.casefold() not in base.casefold()]
    context_query=(base+' '+' '.join(distinct)).strip()[:200]
    # Quoting limits accidental matches and namesake mixing, but cannot verify
    # any person. The analyst still must inspect the original.
    quoted='"'+base.replace('"','').strip()[:130]+'"'
    narrowing='"'+(org or city).replace('"','').strip()[:60]+'"' if (org or city) else ''
    queries=[context_query] if distinct else [base]
    lens=getattr(body,'lens','professional')
    if case['subject_type']=='person':
        if lens=='education':
            queries.extend([quoted+' '+narrowing+' school OR college OR university',
                            quoted+' '+narrowing+' public project OR scholarship OR competition',
                            quoted+' '+narrowing+' public activity OR publication'])
        elif lens=='trade':
            queries.extend([quoted+' '+narrowing+' trade OR service OR business listing',
                            quoted+' '+narrowing+' shop OR contractor OR license',
                            quoted+' '+narrowing+' public events OR professional association'])
        elif lens=='professional':
            queries.extend(['site:linkedin.com/in/ '+quoted+' '+narrowing,
                            'site:github.com '+(('"'+handle.replace('"','')+'"') if handle else quoted)+' '+narrowing,
                            quoted+' '+narrowing+' (portfolio OR CV OR research OR biography)'])
        else:
            queries.extend([quoted+' '+narrowing+' public information',
                            quoted+' '+narrowing+' community OR business OR event',
                            quoted+' '+narrowing+' public profile OR interview OR directory'])
    elif case['subject_type']=='organization':
        queries.extend([quoted+' official website',quoted+' registration OR legal entity',
                        'site:linkedin.com/company/ '+quoted])
    else:
        queries.append(base)
    return list(dict.fromkeys(' '.join(q.split())[:200] for q in queries))[:body.depth]

@router.post('/api/cases/{case_id}/web-discovery')
async def web_discovery(case_id:str,body:WebSearchInput,actor=Depends(core.protect)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        ctx=conn.execute('SELECT city,organization,profession,public_handle FROM case_context WHERE case_id=?',
                         (case_id,)).fetchone()
        saved_plan=conn.execute('SELECT original_question FROM case_search_plans WHERE case_id=?',
                                (case_id,)).fetchone()
    if not body.consent:
        raise HTTPException(422,'Explicit consent is required before sending research queries to Brave Web Search.')
    key=os.getenv('BRAVE_SEARCH_API_KEY','').strip()
    if not key:raise HTTPException(409,'Broad web discovery requires BRAVE_SEARCH_API_KEY in Render private environment. API collectors remain available.')
    context=dict(ctx) if ctx else {}
    original_question=str(saved_plan['original_question']) if saved_plan else case['query']
    search_goal=(body.query or original_question).strip()
    # P0-019: a single first name without a distinguishing public clue is too
    # ambiguous for spending remote search quota or inferring an account.
    if case['subject_type']=='person':
        from .query_parse import parse_question
        parsed=parse_question(search_goal)
        if parsed.identity_state=='given_name_only' and not any(
                str(context.get(k) or '').strip() for k in
                ('city','organization','public_handle')):
            raise HTTPException(422,
                'A single given name is ambiguous. Add a full public name, '
                'public handle or distinguishing organization/city.')
    # P0-020: a user override is explicit; otherwise prefer the full original
    # investigation question over a derived truncated case subject.
    queries=make_queries(case,context,body,original_question)
    runid=core.uid()
    results=[]
    all_candidates=[]
    stop_reason='planned_queries_exhausted'
    async with httpx.AsyncClient(timeout=16,follow_redirects=False) as client:
        for query in queries:
            state='ok';message='';items=[]
            # Pagination is opt-in, limited by the analyst's requested pages
            # and stopped early when there are sufficiently diverse candidate
            # publisher hosts. This does not mean the search is exhaustive.
            for page in range(body.pages):
                try:
                    response=await client.get('https://api.search.brave.com/res/v1/web/search',
                        params={'q':query,'count':12,'offset':page,'safesearch':'strict',
                                'text_decorations':'false','result_filter':'web',
                                'country':body.country,'search_lang':body.search_lang,
                                **({'freshness':body.freshness} if body.freshness!='all' else {})},
                        headers={'X-Subscription-Token':key,'Accept':'application/json'})
                    response.raise_for_status()
                    payload=response.json()
                    for x in payload.get('web',{}).get('results',[])[:12]:
                        url=str(x.get('url',''))
                        if not public_https(url):continue
                        items.append({'title':str(x.get('title') or url)[:200],
                                      'description':str(x.get('description') or '')[:900],
                                      'url':url})
                    decision=coverage_decision(items,queries_executed=page+1,
                                               max_queries=body.pages)
                    if (decision['stop'] or
                        not payload.get('query',{}).get('more_results_available',False)):
                        break
                except (httpx.HTTPError,ValueError,TypeError,KeyError,AttributeError) as exc:
                    state='error'
                    message='Web source unavailable or provider request failed: '+type(exc).__name__
                    break
            items=balance_results(items,max_per_site=3,limit=36)
            if not items and state=='ok':state='empty'
            results.append((query,state,message,items))
            all_candidates.extend(items)
            if body.adaptive:
                coverage=coverage_decision(all_candidates,queries_executed=len(results),
                                           max_queries=len(queries),
                                           provider_error=bool(state=='error'))
                if coverage['stop'] and coverage['reason']!='query_budget_exhausted':
                    stop_reason=coverage['reason']
                    break
    new=0
    revised=0
    with db.connect() as conn:
        for query,status,message,items in results:
            inserted=0
            changed=0
            for item in items:
                raw={'provider':'Brave Web Search','title':item['title'],
                     'snippet':item['description'],'url':item['url'],
                     'searchCountry':body.country,'searchLanguage':body.search_lang,
                     'requestedFreshness':body.freshness,
                     'identity_verified':False,'page_fetched':False}
                disposition=save_observation(conn,case_id=case_id,run_id=runid,
                    query=query,provider='brave_web',
                    source_ref=item['url'][:300],label=item['title'],
                    summary='Public web-search snippet (page not yet captured): '+item['description'],
                    url=item['url'],raw=raw,actor_id=actor['id'])
                inserted+=int(disposition=='new')
                changed+=int(disposition=='changed')
            conn.execute('INSERT INTO research_queries VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (core.uid(),case_id,actor['id'],runid,'brave_web',query,status,
                 len(items),inserted,message or 'Results are unverified web leads',core.iso_now()))
            conn.execute('INSERT INTO collection_runs VALUES (?,?,?,?,?,?,?)',
                (core.uid(),case_id,'brave_web',status,inserted,message or query[:100],core.iso_now()))
            new+=inserted
            revised+=changed
        conn.execute('UPDATE cases SET last_collected=? WHERE id=?',(core.iso_now(),case_id))
    core.write_audit(actor['id'],'web_discovery','case',case_id,f'{len(queries)} queries, {new} saved')
    return {'originalQuestion':original_question,
            'searchGoal':search_goal,
            'queryOrigin':'analyst_override' if body.query else
                          ('original_question' if saved_plan else 'legacy_case_subject'),
            'originalQuestionPreserved':True,
            'queries':[{'query':q,'status':s,'returned':len(items),'newlySaved':'See run history'} for q,s,m,items in results],
            'returned':sum(len(items) for q,s,m,items in results),'new':new,'changed':revised,
            'errors':sum(s=='error' for q,s,m,items in results),
            'publisherHosts':len({x['url'].split('/')[2] for q,s,m,items in results for x in items}),
            'paginationBudget':body.pages,
            'plannedQueries':len(queries),
            'executedQueries':len(results),
            'stopReason':stop_reason,
            'coverage':coverage_decision(all_candidates,queries_executed=len(results),max_queries=len(queries)),
            'indexScope':'Brave public index only; not a web-scale independent local index',
            'notice':'Web results are unverified candidate pages. Manually inspect original sources; do not infer identity.'}

@router.post('/api/cases/{case_id}/evidence/{evidence_id}/capture')
async def capture_source(case_id:str,evidence_id:str,actor=Depends(core.protect)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        record=conn.execute('SELECT id,source_url FROM evidence WHERE id=? AND case_id=?',
            (evidence_id,case_id)).fetchone()
    if not record:raise HTTPException(404,'Evidence source not found in this investigation')
    raw=record['source_url']
    if not capture_allowed(raw):
        raise HTTPException(422,'Automatic retrieval is restricted to a small approved public-host allowlist. Open this source manually instead.')
    try:
        async with httpx.AsyncClient(timeout=13,follow_redirects=False,trust_env=False) as client:
            async with client.stream('GET',raw,headers={'Accept':'text/html,text/plain,application/json',
                     'User-Agent':'OSINTAlpha/5.0-public-evidence-capture'}) as response:
                response.raise_for_status()
                if response.status_code!=200:raise ValueError('Redirected or unavailable page')
                content_type=response.headers.get('content-type','').lower().split(';')[0].strip()
                if content_type not in ('text/html','text/plain','application/json'):
                    raise ValueError('Only public HTML, text and JSON source captures are supported')
                chunks=[]
                count=0
                async for chunk in response.aiter_bytes():
                    count+=len(chunk)
                    if count>MAX_DOWNLOAD:raise ValueError('Source exceeded safe text download limit')
                    chunks.append(chunk)
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(502,'Could not securely capture this public source: '+type(exc).__name__) from exc
    text=extract_text(b''.join(chunks),content_type)
    if len(text)<30:raise HTTPException(422,'The public page did not contain enough visible text to capture reliably.')
    sha=hashlib.sha256(text.encode('utf-8')).hexdigest()
    item_id=core.uid()
    with db.connect() as conn:
        conn.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
            (item_id,case_id,evidence_id,raw,content_type,text,sha,core.iso_now(),'captured',''))
    core.write_audit(actor['id'],'source_capture','evidence',evidence_id,sha[:24])
    return {'id':item_id,'sha256':sha,'length':len(text),'status':'captured',
      'warning':'Extracted text only. Page identity, factual claims and source authenticity are not independently verified.'}

@router.get('/api/cases/{case_id}/evidence/{evidence_id}/captures')
def list_captures(case_id:str,evidence_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        record=conn.execute('SELECT id FROM evidence WHERE id=? AND case_id=?',(evidence_id,case_id)).fetchone()
        if not record:raise HTTPException(404,'Evidence record unavailable')
        rows=conn.execute('SELECT id,source_url,content_type,content_sha256,fetched_at,fetch_status,extracted_text FROM source_captures WHERE case_id=? AND evidence_id=? ORDER BY fetched_at DESC LIMIT 12',(case_id,evidence_id))
        return {'items':[{'id':r['id'],'url':r['source_url'],'contentType':r['content_type'],
                 'sha256':r['content_sha256'],'fetchedAt':r['fetched_at'],'status':r['fetch_status'],
                 'text':r['extracted_text'][:9000]} for r in rows],
                'warning':'Captures are text extracts, not forensic proofs or identity verification.'}
