"""Live Brave LLM Context retrieval for question-specific, consented Groq reasoning.

Search results are source candidates, not certified facts. The model receives
bounded quoted source snippets, while case evidence remains independently reviewed.
No automatic profile merge, image-based identity match, or personal tracking.
"""
from __future__ import annotations

import os
import re
from typing import Any

import httpx
from fastapi import HTTPException

from .v5 import public_https


BLOCKED_LIVE_TRACKING = re.compile(
    r"\b(?:track|locate|follow)\s+(?:this\s+)?person\b|"
    r"\b(?:live|real.time|current)\s+location\s+of\b|"
    r"\b(?:home|residential)\s+address\b|"
    r"\b(?:where\s+is|find)\s+.{0,70}\s+right\s+now\b",
    re.I,
)


def composed_query(case: dict[str, Any], question: str, clues: dict[str, str]) -> str:
    if BLOCKED_LIVE_TRACKING.search(question):
        raise HTTPException(422, 'Live person tracking or residential location searching is not supported.')
    subject = ' '.join(str(case.get('query') or '').split())[:130]
    q = ' '.join(question.split())[:320]
    if not q:
        raise HTTPException(422, 'Enter a public-source research question.')
    hints = []
    for item in ('organization', 'profession', 'city', 'public_handle'):
        value = ' '.join(str(clues.get(item) or '').split())[:60]
        if value and value.casefold() not in (subject + ' ' + q).casefold():
            hints.append(value)
    return ' '.join(([q] if q.casefold().startswith(subject.casefold()) else [subject,q]) + hints)[:570]


def parse_context(payload: dict[str, Any], *, max_sources: int = 7) -> list[dict[str, str]]:
    grounding = payload.get('grounding') or {}
    source_metadata = payload.get('sources') or {}
    if not isinstance(grounding, dict) or not isinstance(source_metadata, dict):
        return []
    entries = grounding.get('generic') or []
    if not isinstance(entries, list):
        return []
    found = []
    urls = set()
    for row in entries[:30]:
        if not isinstance(row, dict):
            continue
        href = str(row.get('url') or '')[:600]
        if not public_https(href) or href in urls:
            continue
        fragments = row.get('snippets')
        if not isinstance(fragments, list):
            fragments = []
        text = ' '.join(str(fragment).strip() for fragment in fragments[:3]
                        if isinstance(fragment, str) and fragment.strip())[:1250]
        if not text:
            continue
        extra = source_metadata.get(href) or {}
        if not isinstance(extra, dict):
            extra = {}
        age = extra.get('age') or []
        stamp = str(age[3])[:80] if isinstance(age, list) and len(age) >= 4 else ''
        found.append({
            'title': str(row.get('title') or extra.get('title') or href)[:200],
            'url': href, 'snippet': text, 'sourceDate': stamp,
            'status': 'unverified_extracted_search_context',
        })
        urls.add(href)
        if len(found) >= max_sources:
            break
    return found


async def retrieve(case: dict[str, Any], question: str, clues: dict[str, str],
                   *, client=None, freshness='all', country='US', search_lang='en', actor_id=None) -> dict[str, Any]:
    key = os.getenv('BRAVE_SEARCH_API_KEY', '').strip()
    if not key:
        raise HTTPException(409, 'BRAVE_SEARCH_API_KEY is not configured on Render.')
    query = composed_query(case, question, clues)
    # Local recall is a business/service search aid, NOT subject-location inference.
    # Only send the city if the analyst explicitly provided the public city and
    # the question asks about publicly listed businesses or service providers.
    city=str(clues.get('city') or '').strip()
    business_intent=bool(re.search(
        r'\b(plumb(?:er|ing)|electrician|contractor|shop|repair|service provider|restaurant|local business|business listing)\b',
        question,re.I))
    local_recall=bool(city and business_intent)
    location_headers=({'X-Loc-City':city[:80],'X-Loc-Country':country}
                      if local_recall else {})
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=14, follow_redirects=False, trust_env=False)
    from .provider_ops import guard as provider_guard, reserve as reserve_paid_call, record as record_health
    import time
    if actor_id is not None:
        provider_guard('brave_context')
        reserve_paid_call(case['id'],actor_id,'brave_context')
    started_remote=time.monotonic()
    try:
        response = await client.post(
            'https://api.search.brave.com/res/v1/llm/context',
            headers={'X-Subscription-Token': key, 'Accept': 'application/json',**location_headers},
            json={
                'q': query, 'count': 12, 'maximum_number_of_urls': 8,
                'maximum_number_of_tokens': 4600, 'maximum_number_of_snippets': 20,
                'context_threshold_mode': 'balanced', 'enable_source_metadata': True,
                'safesearch': 'strict', 'enable_local': local_recall,
                'country':country,'search_lang':search_lang,
                **({'freshness':freshness} if freshness!='all' else {}),
            })
        response.raise_for_status()
        record_health('brave_context','ok',int((time.monotonic()-started_remote)*1000),getattr(response,'status_code',200))
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        record_health('brave_context','throttled' if code==429 else 'unavailable' if code>=500 else 'error',int((time.monotonic()-started_remote)*1000),code)
        label = ('Invalid Brave key or insufficient permissions' if code in (401,403)
                 else 'Brave quota or rate limit reached' if code == 429
                 else 'Brave service returned HTTP ' + str(code))
        raise HTTPException(502, label) from exc
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        if isinstance(exc,httpx.HTTPError):
            record_health('brave_context','unavailable',int((time.monotonic()-started_remote)*1000))
        raise HTTPException(502, 'Brave live context unavailable: ' + type(exc).__name__) from exc
    finally:
        if own_client:
            await client.aclose()
    if not isinstance(payload, dict):
        raise HTTPException(502, 'Brave returned an unexpected response.')
    return {
        'sources': parse_context(payload), 'provider': 'Brave LLM Context',
        'query': query, 'searchedNow': True,'freshness':freshness,
        'jurisdiction':country,'language':search_lang,'localRecall':local_recall,
        'notice': ('These are search-index excerpts from attributed URLs. '
                   'They are not independently verified source-page captures, '
                   'identity matches, live whereabouts, or confirmed claims.')
    }


def clean_answer_links(answer: str, sources: list[dict[str, str]],
                       records: list[dict[str, str]]) -> str:
    """Remove unsupported model-generated Markdown link targets.

    This checks *link existence in retrieved source IDs*, not truth or entailment.
    """
    allowed = {x['url'] for x in sources if x.get('url')}
    allowed.update(str(row.get('url') or '') for row in records)
    def replace_link(match: re.Match) -> str:
        title, href = match.group(1), match.group(2)
        return match.group(0) if href in allowed else title + ' [unverified link omitted]'
    return re.sub(r'\[([^\]]{1,200})\]\((https?://[^)\s]{1,700})\)',
                  replace_link, answer)
