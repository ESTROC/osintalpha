"""Fixed-host API adapters. All external records are candidates, never asserted identity matches.

No arbitrary URL fetch, stealth scraping, private-camera access, or source-driven LLM browsing.
"""
from __future__ import annotations
import asyncio
import hashlib
import html
import re
import json
import ipaddress
import re
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
import httpx


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass(frozen=True)
class Evidence:
    label: str
    summary: str
    url: str
    source_ref: str
    raw: dict
    observed_at: str | None = None


@dataclass(frozen=True)
class Connector:
    id: str
    title: str
    scope: tuple[str, ...]
    description: str
    url: str
    terms: str
    live: bool = True


CATALOG = [
    Connector('github', 'GitHub public profiles', ('person', 'organization'), 'Candidate users and organizations; handles are not identity proof.', 'https://docs.github.com/en/rest/search/search', 'Rate-limited public API'),
    Connector('stackoverflow', 'Stack Overflow public profiles', ('person',), 'Public account-name candidates from Stack Exchange; not identity verification.', 'https://api.stackexchange.com/docs/users', 'Public API; request quotas and availability vary'),
    Connector('openalex', 'OpenAlex authors', ('person',), 'Researcher records and affiliations; name matches are candidates.', 'https://help.openalex.org/api/', 'Free basic budget, limits apply'),
    Connector('crossref', 'Crossref publications', ('person',), 'Publication discovery, not degree validation.', 'https://www.crossref.org/documentation/retrieve-metadata/rest-api/', 'Public metadata API'),
    Connector('gleif', 'GLEIF legal entities', ('organization',), 'Legal Entity Identifier records; no LEI does not mean no company.', 'https://www.gleif.org/en/lei-data/gleif-api/', 'Public LEI reference data'),
    Connector('wikipedia', 'Wikipedia article candidates', ('person', 'organization'), 'Public encyclopedia pages; not an authoritative identity match.', 'https://www.mediawiki.org/wiki/API:Search', 'MediaWiki API / CC BY-SA content'),
    Connector('wikidata', 'Wikidata entity candidates', ('person', 'organization'), 'Structured Wikidata entity search; no automatic person merge.', 'https://www.wikidata.org/w/api.php', 'Wikidata CC0 structured data; API fair use'),
    Connector('gdelt', 'GDELT news references', ('person', 'organization'), 'Possible news mentions; namesakes and allegations require analyst review.', 'https://www.gdeltproject.org/', 'Public API; limits and provider conditions apply'),
]


def canon_record(label, summary, url, key, raw, observed_at=None):
    return Evidence(str(label or 'Untitled')[:240], str(summary or '')[:1500],
                    str(url or '')[:500], str(key or url or label)[:300], raw, observed_at)


class AdapterError(Exception):
    pass


async def get_json(client: httpx.AsyncClient, url: str, params: dict | None = None):
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 429 or code == 403:
            raise AdapterError(f'Provider denied or rate-limited the request (HTTP {code}).') from exc
        raise AdapterError(f'Provider returned HTTP {code}.') from exc
    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
        raise AdapterError(f'Provider unavailable: {type(exc).__name__}.') from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise AdapterError('Provider returned invalid JSON.') from exc


async def github(client, query, subject_type):
    """Search public GitHub display names, then enrich candidates from public profiles."""
    words=[w for w in re.split(r'\s+',query.strip()) if w]
    if not words:
        return []
    kind='user' if subject_type=='person' else 'org'
    # Official GitHub user-search qualifier is in:name, NOT in:fullname.
    search_q=f'{" ".join(words)} in:name type:{kind}'
    obj=await get_json(client,'https://api.github.com/search/users',{'q':search_q,'per_page':12})
    accounts=[row for row in obj.get('items',[]) if isinstance(row,dict)][:12]
    # Treat a known public username as an exact account lookup. A display-name
    # search is not sufficient to resolve a handle, and a name match must never
    # silently confirm profile ownership.
    if len(words)==1 and re.fullmatch(r'[A-Za-z0-9-]{1,39}',words[0]):
        try:
            direct=await get_json(client,'https://api.github.com/users/'+words[0])
            if str(direct.get('login','')).casefold()==words[0].casefold():
                accounts=[{'login':direct['login'],'id':direct.get('id') or direct['login']}] + [
                    x for x in accounts if str(x.get('login','')).casefold()!=words[0].casefold()]
        except (AdapterError,httpx.HTTPError,ValueError):
            pass
    if not accounts:
        # Username-only fallback if a public account doesn't expose a real name.
        compact=''.join(words)
        obj=await get_json(client,'https://api.github.com/search/users',{'q':f'{compact} in:login type:{kind}','per_page':8})
        accounts=[row for row in obj.get('items',[]) if isinstance(row,dict)][:8]
    async def enrich(row):
        login=str(row.get('login') or '')
        if not re.fullmatch(r'[A-Za-z0-9-]{1,39}',login):
            return None
        public_profile={}
        try:
            # A search result is already a candidate; enrichment is best-effort
            # and must not discard leads when profile API is rate-limited.
            public_profile=await get_json(client,'https://api.github.com/users/'+login)
        except (AdapterError,httpx.HTTPError,ValueError):
            pass
        display=str(public_profile.get('name') or login).strip()[:140]
        parts=[str(public_profile[k]).strip()[:120] for k in ('bio','company','location')
               if public_profile.get(k)]
        if public_profile.get('public_repos') is not None:
            parts.append(f"Public repositories: {public_profile.get('public_repos')}")
        summary=('Public GitHub account candidate (@'+login+'). '+
                 (' | '.join(parts)+'. ' if parts else '')+
                 'No ownership or identity match has been established.')
        return canon_record(display,summary,
            'https://github.com/'+login,str(row.get('id') or login),
            {'login':login,'display_name':display,
             'bio':str(public_profile.get('bio') or '')[:200],
             'company':str(public_profile.get('company') or '')[:150],
             'location':str(public_profile.get('location') or '')[:100],
             'public_repos':public_profile.get('public_repos'),
             'avatar_url':str(public_profile.get('avatar_url') or '')[:400],
             'blog':str(public_profile.get('blog') or '')[:250],
             'html_url':'https://github.com/'+login,
             'kind':kind,'identity_verified':False})
    items=await asyncio.gather(*(enrich(a) for a in accounts[:8]))
    return [x for x in items if x is not None]


async def stackoverflow(client, query, subject_type):
    """Public Stack Overflow user display names; not verified as this individual."""
    q=' '.join(query.strip().split())
    if len(q)<3:
        return []
    obj=await get_json(client,'https://api.stackexchange.com/2.3/users',
        {'site':'stackoverflow','inname':q,'sort':'reputation','order':'desc','pagesize':20})
    if not isinstance(obj,dict):
        raise AdapterError('Stack Exchange returned an unexpected response.')
    if obj.get('error_id'):
        raise AdapterError('Stack Exchange rejected the search: '+str(obj.get('error_name','unknown')))
    wanted=[w.casefold() for w in q.split() if len(w)>=2]
    candidates=[]
    for row in obj.get('items',[])[:20]:
        if not isinstance(row,dict): continue
        name=html.unescape(str(row.get('display_name') or '')).strip()
        # Only retain full-token matches, avoiding unrelated namesakes.
        tokens=re.findall(r'\w+',name.casefold())
        if not name or not all(word in tokens for word in wanted):
            continue
        uid=row.get('user_id')
        if not isinstance(uid,int) or uid<=0: continue
        profile='https://stackoverflow.com/users/'+str(uid)
        rep=row.get('reputation')
        location=html.unescape(str(row.get('location') or ''))[:100]
        summary=(f'Public Stack Overflow profile candidate; reputation: {rep if isinstance(rep,int) else "unknown"}.'+
                 (f' Listed location: {location}.' if location else '')+
                 ' Public display-name match only; identity and account ownership are unverified.')
        candidates.append(canon_record(name,summary,profile,str(uid),
            {'user_id':uid,'display_name':name,'reputation':rep,
             'location':location,'identity_verified':False}))
        if len(candidates)>=8:break
    return candidates


async def openalex(client, query, subject_type):
    obj = await get_json(client, 'https://api.openalex.org/authors', {'search': query, 'per-page': 8})
    items = []
    for a in obj.get('results', [])[:8]:
        inst = [i.get('display_name') for i in (a.get('last_known_institutions') or []) if isinstance(i, dict)]
        items.append(canon_record(a.get('display_name'), f"Author candidate. Works: {a.get('works_count', '?')}; listed institutions: {', '.join(inst) or 'not listed'}. Not a verified qualification.", a.get('id'), a.get('id'),
            {'id': a.get('id'), 'name': a.get('display_name'), 'works_count': a.get('works_count'), 'institutions': inst,
             'orcid': a.get('orcid'), 'identity_verified':False}))
    return items


async def crossref(client, query, subject_type):
    """Only retain papers that actually list an author matching the query's name.

    Crossref query.author searches metadata broadly and can return partial-name
    matches across DIFFERENT authors on one work. This is not identity proof.
    """
    obj=await get_json(client,'https://api.crossref.org/works',
        {'query.author':query,'rows':20,'select':'DOI,title,author,published,URL'})
    target=re.findall(r'[a-z0-9]+',query.casefold())
    def matching_author(author):
        name=(str(author.get('given',''))+' '+str(author.get('family',''))).strip()
        parts=re.findall(r'[a-z0-9]+',name.casefold())
        if not parts or not target:return False
        if len(target)==1:return target[0] in parts
        # Exact first/last names; tolerate middle initials, never match
        # first and last words belonging to two different coauthors.
        return parts[0]==target[0] and parts[-1]==target[-1] and len(parts)<=len(target)+2
    found=[]
    for w in obj.get('message',{}).get('items',[])[:20]:
        authors=[a for a in w.get('author',[]) if isinstance(a,dict)]
        if not any(matching_author(a) for a in authors):
            continue
        title=(w.get('title') or ['Untitled'])[0]
        named=', '.join((a.get('given','')+' '+a.get('family','')).strip() for a in authors[:6])
        doi=str(w.get('DOI') or '')
        found.append(canon_record(title,'Publication author-name match. Authors: '+named+
                '. Same-name authors may be different people. This does not confirm education or identity.',
                'https://doi.org/'+quote(doi,safe='/') if doi else w.get('URL'),
                doi or title,{'title':title,'doi':doi,'authors':named,'identity_verified':False}))
        if len(found)>=10:break
    return found


async def gleif(client, query, subject_type):
    obj = await get_json(client, 'https://api.gleif.org/api/v1/lei-records', {'filter[fulltext]': query, 'page[size]': 8})
    out = []
    for row in obj.get('data', [])[:8]:
        attrs = row.get('attributes') or {}
        entity = attrs.get('entity') or {}
        ln = entity.get('legalName') or {}
        name = ln.get('name') if isinstance(ln, dict) else str(ln)
        lei = row.get('id') or attrs.get('lei') or ''
        out.append(canon_record(name or 'Registered entity', f"LEI record candidate. Registration status: {entity.get('status', 'not supplied')}.",
                    f'https://search.gleif.org/#/record/{lei}', lei, {'lei': lei, 'name': name, 'status': entity.get('status')}))
    return out


async def wikipedia(client, query, subject_type):
    obj = await get_json(client, 'https://en.wikipedia.org/w/api.php', {'action': 'query', 'list': 'search', 'srsearch': query, 'srlimit': 6, 'format': 'json'})
    return [canon_record(x.get('title'), 'Public encyclopedia candidate. Open the page and evaluate independent sources.',
           'https://en.wikipedia.org/wiki/' + quote(x.get('title', '').replace(' ', '_')), str(x.get('pageid')),
           {'title': x.get('title'), 'pageid': x.get('pageid')}) for x in obj.get('query', {}).get('search', [])]




async def wikidata(client, query, subject_type):
    obj=await get_json(client, 'https://www.wikidata.org/w/api.php',
        {'action':'wbsearchentities','search':query,'language':'en','format':'json','limit':8})
    out=[]
    for item in obj.get('search',[])[:8]:
        ident=item.get('id','')
        if not ident.startswith('Q'): continue
        out.append(canon_record(item.get('label') or ident,
              'Wikidata entity candidate: '+str(item.get('description') or 'No description available.')+'. Verify entity identity and primary sources.',
              'https://www.wikidata.org/wiki/'+ident,ident,
              {'id':ident,'label':item.get('label'),'description':item.get('description')}))
    return out


async def gdelt(client, query, subject_type):
    # GDELT articles are search leads; article text is not scraped or assumed true.
    obj=await get_json(client,'https://api.gdeltproject.org/api/v2/doc/doc',
         {'query':'"'+query.replace('"','')+'"','mode':'artlist','format':'json','maxrecords':12,'sort':'datedesc'})
    out=[]
    for row in obj.get('articles',[])[:12]:
        link=row.get('url','')
        if not link.startswith('https://') and not link.startswith('http://'): continue
        out.append(canon_record(row.get('title') or 'Article candidate',
               'News article mentioning search terms. Identity, allegations and article accuracy not verified. '+str(row.get('domain','')),
               link,link,{'title':row.get('title'),'domain':row.get('domain'),'seendate':row.get('seendate')},row.get('seendate')))
    return out

FUNCTIONS = {'wikidata':wikidata, 'gdelt':gdelt,'github': github, 'stackoverflow':stackoverflow, 'openalex': openalex, 'crossref': crossref, 'gleif': gleif, 'wikipedia': wikipedia}


async def collect_one(provider, query, subject_type, client=None):
    connector = next((c for c in CATALOG if c.id == provider), None)
    if connector is None or subject_type not in connector.scope:
        raise AdapterError('Unknown source or incompatible subject type.')
    if client:
        return await FUNCTIONS[provider](client, query, subject_type)
    async with httpx.AsyncClient(timeout=12, headers={'User-Agent': 'OSINT AlphaResearchWorkbench/0.1 (authorized research demo)'}, follow_redirects=False) as c:
        return await FUNCTIONS[provider](c, query, subject_type)


async def geo_events(kind, client=None):
    if kind not in {'earthquakes', 'nasa'}:
        raise AdapterError('Unknown geospatial feed.')
    if client is None:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as c:
            return await geo_events(kind, c)
    if kind == 'earthquakes':
        obj = await get_json(client, 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson')
        out = []
        for f in obj.get('features', [])[:160]:
            coords = (f.get('geometry') or {}).get('coordinates') or []
            if len(coords) < 2: continue
            p = f.get('properties') or {}
            out.append({'id': f.get('id'), 'type': 'earthquake', 'provider': 'USGS', 'name': p.get('place') or 'Earthquake',
                        'lat': coords[1], 'lon': coords[0], 'value': p.get('mag'), 'observedAt': p.get('time'), 'url': p.get('url')})
        return out
    obj = await get_json(client, 'https://eonet.gsfc.nasa.gov/api/v3/events', {'status': 'open', 'limit': 90})
    out = []
    for event in obj.get('events', []):
        geom = event.get('geometry') or []
        pt = geom[-1] if geom else {}
        coords = pt.get('coordinates') or []
        if pt.get('type') != 'Point' or len(coords) < 2: continue
        out.append({'id': event.get('id'), 'type': 'natural_event', 'provider': 'NASA EONET', 'name': event.get('title'),
                    'lat': coords[1], 'lon': coords[0], 'value': (event.get('categories') or [{}])[0].get('title'),
                    'observedAt': pt.get('date'), 'url': event.get('link')})
    return out


async def tfl_cameras(client=None):
    key = os.getenv('TFL_APP_KEY', '').strip()
    if not key:
        raise AdapterError('TfL APP_KEY not configured. Camera discovery disabled; open official provider/project links instead.')
    if client is None:
        async with httpx.AsyncClient(timeout=15) as c:
            return await tfl_cameras(c)
    obj = await get_json(client, 'https://api.tfl.gov.uk/Place/Type/JamCam', {'app_key': key})
    out = []
    for row in (obj if isinstance(obj, list) else [])[:220]:
        props = row.get('additionalProperties') or []
        imgs = [p.get('value') for p in props if p.get('key') == 'imageUrl']
        lat, lon = row.get('lat'), row.get('lon')
        if lat is None or lon is None: continue
        out.append({'id': row.get('id'), 'type': 'camera', 'provider': 'TfL', 'name': row.get('commonName') or 'London JamCam',
                    'lat': lat, 'lon': lon, 'url': 'https://tfl.gov.uk/traffic/status/',
                    'feedUrl': imgs[0] if imgs else None, 'observedAt': None,
                    'value': 'Publisher camera listing; capture time not established'})
    return out


OSS_PROJECTS = [
    {'id':'osiris','name':'OSIRIS','category':'Geo intelligence','strength':'Layer-rich map and CCTV source modules','repo':'https://github.com/simplifaisoul/osiris','live':'https://osirisai.live/','license':'MIT','integration':'Upstream reference / adapter candidate'},
    {'id':'gods-eye-view','name':"God's Eye View",'category':'Geo intelligence','strength':'3D globe and recent imagery layers','repo':'https://github.com/bilawalsidhu/gods-eye-view','live':'','license':'MIT code; mixed data rights','integration':'External launch / future visual mode'},
    {'id':'worldmonitor','name':'World Monitor','category':'Geo intelligence','strength':'News and event monitoring','repo':'https://github.com/koala73/worldmonitor','live':'https://www.worldmonitor.app/','license':'AGPL core; MIT clients','integration':'External launch / licensed service only'},
    {'id':'argus','name':'Argus','category':'Camera intelligence','strength':'Camera catalog, parsers, GeoJSON export','repo':'https://github.com/GoSlowPoke168/Argus','live':'','license':'MIT code','integration':'Adapter candidate'},
    {'id':'camforge','name':'CamForge','category':'Camera intelligence','strength':'Public-by-design camera relay patterns','repo':'https://github.com/SoCloseSociety/camforge','live':'','license':'MIT code','integration':'Adapter candidate / not deployed'},
    {'id':'spiderfoot','name':'SpiderFoot','category':'OSINT collection','strength':'Numerous collection modules','repo':'https://github.com/smicallef/spiderfoot','live':'','license':'MIT','integration':'External source engine candidate'},
    {'id':'maigret','name':'Maigret','category':'Identity discovery','strength':'Username candidate searches','repo':'https://github.com/soxoj/maigret','live':'','license':'MIT','integration':'Not enabled; false-positive review required'},
    {'id':'sherlock','name':'Sherlock','category':'Identity discovery','strength':'Username presence leads','repo':'https://github.com/sherlock-project/sherlock','live':'','license':'MIT','integration':'Not enabled; requires verification'},
    {'id':'openaleph','name':'OpenAleph','category':'Evidence management','strength':'Document search and investigative datasets','repo':'https://github.com/openaleph/openaleph','live':'','license':'Review components','integration':'External engine candidate'},
    {'id':'followthemoney','name':'FollowTheMoney','category':'Entity graph','strength':'Entity schema and normalization','repo':'https://github.com/opensanctions/followthemoney','live':'','license':'MIT','integration':'Future schema adapter'},
    {'id':'archivebox','name':'ArchiveBox','category':'Evidence management','strength':'Web archive capture','repo':'https://github.com/ArchiveBox/ArchiveBox','live':'','license':'MIT','integration':'Optional source archive service'},
    {'id':'pywb','name':'pywb','category':'Evidence management','strength':'WARC replay','repo':'https://github.com/webrecorder/pywb','live':'','license':'Apache-2.0','integration':'Optional authorized archive service'},
    {'id':'dedupe','name':'Dedupe','category':'Identity resolution','strength':'Human-guided record linkage','repo':'https://github.com/dedupeio/dedupe','live':'','license':'MIT','integration':'Future candidate suggestions'},
    {'id':'intelowl','name':'IntelOwl','category':'Threat intelligence','strength':'Security indicator enrichment','repo':'https://github.com/intelowlproject/IntelOwl','live':'','license':'AGPL; check applicable version','integration':'Not embedded; license review'},
    {'id':'opencti','name':'OpenCTI','category':'Threat intelligence','strength':'Cyber intelligence graph','repo':'https://github.com/OpenCTI-Platform/opencti','live':'','license':'Apache-2.0 core; review add-ons','integration':'External engine candidate'},
    {'id':'nasa-worldview','name':'NASA Worldview','category':'Satellites','strength':'Satellite imagery and observation dates','repo':'https://github.com/nasa-gibs/worldview','live':'https://worldview.earthdata.nasa.gov/','license':'Check source asset terms','integration':'External launch'},
    {'id':'copernicus','name':'Copernicus Browser','category':'Satellites','strength':'Sentinel imagery discovery','repo':'https://github.com/sentinel-hub','live':'https://browser.dataspace.copernicus.eu/','license':'Provider data terms','integration':'External launch / future API'},
    {'id':'bellingcat','name':'Bellingcat Toolkit','category':'Verification','strength':'Curated verification tools','repo':'https://github.com/bellingcat/toolkit','live':'https://bellingcat.gitbook.io/toolkit','license':'Repository-specific','integration':'Research library'},
]


async def caltrans_cameras(client=None):
    """Public transport authority metadata. Only link to official image listings."""
    if client is None:
        async with httpx.AsyncClient(timeout=18, follow_redirects=False) as c:
            return await caltrans_cameras(c)
    obj=await get_json(client,
        'https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/CCTV/FeatureServer/0/query',
        {'where':'1=1','outFields':'OBJECTID,latitude,longitude,locationName,currentImageURL,county,nearbyPlace',
         'returnGeometry':'false','resultRecordCount':300,'f':'json'})
    out=[]
    for f in obj.get('features',[]):
        attrs=f.get('attributes') or {}
        lat=attrs.get('latitude');lon=attrs.get('longitude')
        if not isinstance(lat,(int,float)) or not isinstance(lon,(int,float)) or not -90<=lat<=90 or not -180<=lon<=180: continue
        out.append({'id':'caltrans-'+str(attrs.get('OBJECTID')), 'type':'camera','provider':'Caltrans official CCTV metadata',
           'name':attrs.get('locationName') or 'California highway camera', 'lat':lat,'lon':lon,
           'url':'https://cwwp2.dot.ca.gov/vm/','feedUrl':attrs.get('currentImageURL'),
           'observedAt':None,'value':attrs.get('county') or 'Image capture time not established'})
    return out


# V2: read-only, fixed-host defensive enrichment. These are integrated adapters,
# NOT claims that external security tools have been installed.
DOMAIN_PATTERN = re.compile(r'^(?=.{4,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$')

def valid_domain(value: str) -> bool:
    value=value.strip().rstrip('.')
    return bool(DOMAIN_PATTERN.fullmatch(value)) and not value.lower().endswith(('.local','.internal','.localhost','.test','.example','.invalid'))

def valid_public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value.strip()).is_global
    except ValueError:
        return False

async def dns_records(client, query, kind):
    """Google Public DNS-over-HTTPS, three limited DNS record types, no active scan."""
    domain=query.strip().rstrip('.').lower()
    if not valid_domain(domain):
        raise AdapterError('Enter a valid public domain, without URL paths or wildcards.')
    out=[]
    for record_type in ('A','MX','NS'):
        obj=await get_json(client,'https://dns.google/resolve',{'name':domain,'type':record_type})
        status=obj.get('Status')
        if status not in (0,3):
            raise AdapterError('DNS lookup returned an error status: '+str(status))
        answers=[x for x in (obj.get('Answer') or []) if isinstance(x,dict)]
        values=[str(a.get('data','')).strip()[:180] for a in answers if a.get('data')]
        if values:
            out.append(canon_record(f'{record_type} records · {domain}',
                    f'{len(values)} public DNS answer(s): '+', '.join(values[:8])+
                    '. DNS observations can change and do not establish domain ownership.',
                    'https://dns.google/query?name='+domain+'&type='+record_type,domain+':'+record_type,
                    {'domain':domain,'recordType':record_type,'answers':values[:15],
                     'resolver':'Google Public DNS','rcode':status}))
    return out

async def internetdb(client, query, kind):
    """Shodan InternetDB passive enrichment; never initiates port scans."""
    ip=query.strip()
    if not valid_public_ip(ip):
        raise AdapterError('Only public globally routable IP addresses are accepted.')
    url='https://internetdb.shodan.io/'+ip
    try:
        res=await client.get(url)
        if res.status_code == 404:
            return []
        res.raise_for_status()
        obj=res.json()
    except httpx.HTTPStatusError as exc:
        raise AdapterError('Shodan InternetDB returned HTTP '+str(exc.response.status_code)) from exc
    except (httpx.TimeoutException,httpx.ConnectError,httpx.NetworkError) as exc:
        raise AdapterError('InternetDB unavailable: '+type(exc).__name__) from exc
    except ValueError as exc:
        raise AdapterError('InternetDB returned invalid JSON') from exc
    if not isinstance(obj,dict):
        raise AdapterError('InternetDB returned an unexpected response format')
    ports=[p for p in obj.get('ports',[]) if isinstance(p,int) and 0<p<65536][:40]
    vulns=[str(v)[:32] for v in obj.get('vulns',[]) if isinstance(v,str)][:40]
    names=[str(x)[:160] for x in obj.get('hostnames',[]) if isinstance(x,str)][:15]
    tags=[str(x)[:100] for x in obj.get('tags',[]) if isinstance(x,str)][:20]
    if not ports and not vulns and not names and not tags:
        return []
    # CVE indicators are provider assertions, NOT proofs of current exploitation.
    summary=(f'Passive snapshot: {len(ports)} reported ports; {len(vulns)} CVE references; '
             f'{len(names)} hostnames. Reported ports: {", ".join(map(str,ports[:12])) or "none"}. '
             'Findings may be stale or inaccurate; never treat CVE presence as verified vulnerability.')
    return [canon_record('Passive network exposure · '+ip,summary,
            'https://www.shodan.io/host/'+ip,'shodan:'+ip,
            {'ip':ip,'ports':ports,'vulns':vulns,'hostnames':names,'tags':tags,
             'cpes':obj.get('cpes',[])[:35] if isinstance(obj.get('cpes'),list) else [],
             'mode':'passive','verified':False})]

CATALOG.extend([
    Connector('dns','Google Public DNS',('domain',),
        'Passive A, MX and NS records from a public resolver; not a security scan.',
        'https://developers.google.com/speed/public-dns/docs/doh',
        'Keyless official resolver API; rate limits apply'),
    Connector('internetdb','Shodan InternetDB',('ip',),
        'Passive IP observation metadata: ports, CVEs, hostnames and tags. Not current verification.',
        'https://book.shodan.io/developer-apis/internetdb/',
        'Keyless read-only enrichment; incomplete and potentially stale')
])
FUNCTIONS.update({'dns':dns_records,'internetdb':internetdb})
