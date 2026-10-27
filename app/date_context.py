"""Explicit historical page-index window and date provenance, not event-date inference."""
from datetime import date, datetime
import re
from fastapi import HTTPException


def parse_date(value):
    try:return date.fromisoformat(value)
    except (ValueError,TypeError) as exc:
        raise HTTPException(422,'Enter a valid ISO YYYY-MM-DD date.') from exc


def historical_window(question):
    text=str(question or '').casefold()
    # Extract only explicit date-search intentions, not random years in names.
    m=re.search(r'\b(?:between|from)\s+((?:19|20)\d{2})\s+(?:and|to|through|-)\s+((?:19|20)\d{2})\b',text)
    if m:
        first,last=int(m.group(1)),int(m.group(2))
        if last<first:raise HTTPException(422,'Historical date range is reversed.')
        return (f'{first}-01-01',f'{last}-12-31')
    m=re.search(r'\b(?:in|during|throughout)\s+((?:19|20)\d{2})\b',text)
    if m:return (f'{m.group(1)}-01-01',f'{m.group(1)}-12-31')
    return None


def resolve_page_window(question,date_from=None,date_to=None,freshness='all'):
    explicit=bool(date_from or date_to)
    extracted=historical_window(question) if not explicit else None
    if explicit and (not date_from or not date_to):
        raise HTTPException(422,'Provide both date_from and date_to.')
    if explicit or extracted:
        if freshness!='all':
            raise HTTPException(422,'Do not combine a historical interval with relative freshness.')
        start,end=(date_from,date_to) if explicit else extracted
        first,last=parse_date(start),parse_date(end)
        if first>last:raise HTTPException(422,'Start date cannot be later than end date.')
        return {'freshness':f'{first.isoformat()}to{last.isoformat()}',
                'intervalFrom':first.isoformat(),'intervalTo':last.isoformat(),
                'appliesTo':'Brave indexed page published/modified date',
                'derivedFrom':'explicit_fields' if explicit else 'question_period',
                'eventDateVerified':False}
    return {'freshness':freshness,'intervalFrom':None,'intervalTo':None,
            'appliesTo':'Brave indexed page published/modified date' if freshness!='all' else 'none',
            'derivedFrom':'relative_filter' if freshness!='all' else 'none',
            'eventDateVerified':False}


def date_provenance(result,retrieved_at):
    value=result if isinstance(result,dict) else {}
    # Provider page_age may be human text or ISO; do not relabel it publication.
    return {'publisherEventDate':None,'publisherPublicationDate':None,
        'indexedPageAgeOrModification':str(value.get('page_age') or '')[:80] or None,
        'providerPageFetchedAt':str(value.get('page_fetched') or '')[:80] or None,
        'systemRetrievedAt':retrieved_at,
        'provenanceWarning':'Indexed page age may be last modified, not published or event date.'}
