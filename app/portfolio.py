"""Reviewable, case-scoped public profile candidates and coarse map previews.

This module does not compile dossiers by automatic identity merging.
All returned records retain independent original-source identities.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import db
from . import main as core
from .identity import attributes, rank_against_clues

router = APIRouter()
PROFILE_PROVIDERS = {'github', 'stackoverflow', 'openalex', 'brave_web', 'analyst'}
_GEOCODE_LOCK = asyncio.Lock()
_GEOCODE_LAST = 0.0
_GEOCODE_CACHE: dict[str, tuple[float, dict]] = {}


def classify_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or '').lower().rstrip('.')
        path = parsed.path.lower()
        if parsed.scheme != 'https':
            return 'other_public_page'
        if host in {'linkedin.com', 'www.linkedin.com'} and (
                path.startswith('/in/') or path.startswith('/pub/')):
            return 'linkedin_lead'
        if host == 'github.com' or host == 'www.github.com':
            return 'github'
        if host in {'orcid.org', 'www.orcid.org'}:
            return 'orcid'
        if host in {'scholar.google.com'}:
            return 'scholar'
        if host in {'openalex.org', 'www.openalex.org'}:
            return 'openalex'
    except (TypeError, ValueError):
        pass
    return 'other_public_page'


def safe_github_avatar(value: object) -> str:
    """Only public GitHub avatar CDN media; never a search-result image guess."""
    if not isinstance(value, str) or len(value) > 400:
        return ''
    try:
        parsed = urlsplit(value)
        if parsed.scheme == 'https' and parsed.hostname == 'avatars.githubusercontent.com' \
                and not parsed.username and not parsed.password \
                and parsed.port in (None, 443) and parsed.path.startswith('/u/'):
            return value
    except ValueError:
        pass
    return ''


@router.get('/api/cases/{case_id}/public-portfolio')
def public_portfolio(case_id: str, actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        case = core.case_or_404(conn, case_id, actor)
        ctx = conn.execute(
            'SELECT city,organization,profession,public_handle FROM case_context WHERE case_id=?',
            (case_id,)).fetchone()
        context = dict(ctx) if ctx else {}
        rows = [dict(row) for row in conn.execute(
            '''SELECT id,provider,label,summary,source_url,raw_json,status,fetched_at
               FROM evidence WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT 500''',
            (case_id,))]
    candidates = []
    for row in rows:
        if row['provider'] not in PROFILE_PROVIDERS or row['status'] == 'rejected':
            continue
        try:
            raw = json.loads(row.get('raw_json') or '{}')
        except (TypeError, ValueError):
            raw = {}
        if not isinstance(raw, dict):
            raw = {}
        source_kind = classify_url(row['source_url'])
        # Generic web pages are also useful public leads for students, trades,
        # community events and local services. Keep them visibly separate from
        # actual profile/account metadata; never claim they represent this person.
        parsed = attributes(row)
        photo = safe_github_avatar(raw.get('avatar_url')) if row['provider'] == 'github' else ''
        website = str(raw.get('blog') or '')[:250] if row['provider'] == 'github' else ''
        candidate = {
            'evidenceId': row['id'], 'platform': ('public_web_lead' if source_kind == 'other_public_page' else source_kind)
                        if row['provider'] == 'brave_web' else row['provider'],
            'isProfileAccount': row['provider'] != 'brave_web' or source_kind != 'other_public_page',
            'sourceProvider': row['provider'], 'sourceUrl': row['source_url'],
            'displayName': parsed['name'] or row['label'],
            'organization': parsed['organization'], 'publishedLocation': parsed['location'],
            'publicHandle': parsed['publicHandle'], 'photoUrl': photo,
            'website': website if website.startswith('https://') else '',
            'summary': row['summary'][:420], 'reviewStatus': row['status'],
            'retrievedAt': row['fetched_at'], 'clues': rank_against_clues(parsed, context),
            'identityVerified': False,
            'note': ('Search lead only; it is not necessarily a profile or a record about the case subject. Original page not verified.'
                     if row['provider'] == 'brave_web'
                     else 'Publisher metadata about a candidate account; ownership has not been verified.')
        }
        candidates.append(candidate)
    candidates.sort(key=lambda item: (
        -len(item['clues']['matched']), len(item['clues']['different']),
        0 if item['sourceProvider'] != 'brave_web' else 1, item['displayName'].casefold()))
    return {
        'subjectType': case['subject_type'], 'subjectQuery': case['query'],
        'contextCity': context.get('city') or '', 'items': candidates[:200],
        'total': len(candidates), 'verifiedProfiles': 0,
        'notice': ('Independent profiles are not automatically joined. A displayed photo belongs '
                   'to a candidate public account, not necessarily the investigated person. '
                   'LinkedIn links are search leads, not scraped or confirmed LinkedIn profiles.')
    }


class CoarseLocationRequest(BaseModel):
    consent: bool = False


def public_city_only(value: str) -> str:
    name = ' '.join(str(value or '').strip().split())
    if (not name or len(name) > 80 or any(char.isdigit() for char in name)
            or re.search(r'\b(street|road|lane|house|flat|apartment|building|block|sector|pin|postcode|zip)\b', name, re.I)
            or not re.fullmatch(r"[\w ,.'()\-]+", name, flags=re.UNICODE)):
        return ''
    return name


@router.post('/api/cases/{case_id}/public-location-preview')
async def public_location_preview(case_id: str, body: CoarseLocationRequest,
                                  actor=Depends(core.protect)):
    """Only analyst-supplied city/region, by explicit opt-in; never subject location."""
    with db.connect() as conn:
        core.case_or_404(conn, case_id, actor)
        row = conn.execute('SELECT city FROM case_context WHERE case_id=?', (case_id,)).fetchone()
    city = public_city_only(row['city'] if row else '')
    if not city:
        raise HTTPException(422, 'Add only a public city or region clue, not an address, to preview a map.')
    if not body.consent:
        raise HTTPException(422, 'Authorize sending this coarse place name to OpenStreetMap Nominatim.')
    cache_key = city.casefold()
    cached = _GEOCODE_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < 86_400:
        return cached[1]
    global _GEOCODE_LAST
    async with _GEOCODE_LOCK:
        cached = _GEOCODE_CACHE.get(cache_key)
        if cached and time.monotonic() - cached[0] < 86_400:
            return cached[1]
        elapsed = time.monotonic() - _GEOCODE_LAST
        if elapsed < 1.1:
            await asyncio.sleep(1.1 - elapsed)
        _GEOCODE_LAST = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
                result = await client.get(
                    'https://nominatim.openstreetmap.org/search',
                    params={'q': city, 'format': 'jsonv2', 'addressdetails': 1, 'limit': 3},
                    headers={'User-Agent': 'OSINTAlpha/7.7 (https://github.com/ESTROC/osintalpha)',
                             'Accept': 'application/json'})
                result.raise_for_status()
                matches = result.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, 'Public city lookup unavailable: ' + type(exc).__name__) from exc
        if not isinstance(matches, list) or not matches:
            raise HTTPException(404, 'The coarse public city or region could not be located.')
        # Map the settlement centroid, not an address or a person's actual position.
        record = matches[0]
        try:
            lat, lon = round(float(record['lat']), 2), round(float(record['lon']), 2)
            if abs(lat) > 90 or abs(lon) > 180:
                raise ValueError('invalid coordinates')
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(502, 'Place provider returned invalid coordinates.') from exc
        response = {
            'cityClue': city, 'label': str(record.get('display_name') or city)[:180],
            'lat': lat, 'lon': lon, 'precision': 'approximate city/region centre',
            'ambiguous': len(matches) > 1, 'source': 'OpenStreetMap Nominatim',
            'notice': 'This plots an analyst-supplied public geographic clue, NOT the current or residential location of any individual.',
            'attribution': '© OpenStreetMap contributors'}
        if len(_GEOCODE_CACHE) > 500:
            _GEOCODE_CACHE.clear()
        _GEOCODE_CACHE[cache_key] = (time.monotonic(), response)
        return response
