"""Case-scoped public trade/registry leads; never represent an unlicensed index as a registry.

No personal phone scraping, address inference or automatic person identity linkage.
Indian registry links are manually inspected; external registry APIs are NOT integrated.
"""
from __future__ import annotations
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends
from . import main as core,db

router=APIRouter()
OCCUPATION_LENSES={
  'trade':{'tokens':('plumber','electrician','repair','shop','contractor','vendor','salon','carpenter'),
           'queries':('public business listing','registered service provider','trade association'),
           'purpose':'Public trade/business postings, not private addresses or licenses'},
  'education':{'tokens':('student','school','college','university','scholarship','campus'),
           'queries':('site:ac.in public award','site:edu.in public event'),
           'purpose':'Published institutional announcements, never private student records'},
  'professional':{'tokens':('engineer','researcher','scientist','developer'),
           'queries':('public profile','published professional association'),
           'purpose':'Public portfolio and occupational records, not employer verification'},
}
REGISTRY_REFERENCE=[
    {'id':'india_mca','display':'MCA Company Master Details',
     'link':'https://www.mcacdm.nic.in/company-master-details',
     'access':'manual_official_page_review','verifiedIntegratedAPI':False,
     'coverage':'Indian company/LLP public master details; not a complete record of every local trade'},
    {'id':'india_gst','display':'GST Portal',
     'link':'https://www.gst.gov.in/',
     'access':'manual_official_site_review','verifiedIntegratedAPI':False,
     'coverage':'GST registration lookup where authorized and eligible; a missing GST match is not proof a business is nonexistent'},
]
def occupation_routes(question):
    q=' '.join(str(question or '').casefold().split())
    out=[]
    for name,metadata in OCCUPATION_LENSES.items():
        if any(token in q for token in metadata['tokens']):
            out.append({'lens':name,'suggestedQueries':metadata['queries'],
                        'purpose':metadata['purpose'],'liveConnectorProvisioned':False})
    return out

def _public_profile(e):
    from urllib.parse import urlsplit
    url=str(e.get('source_url') or '')
    if urlsplit(url).scheme!='https':return None
    label=str(e.get('label') or '').strip()[:200]
    # Do not hallucinate business address, contacts, or registration from excerpts.
    return {'evidenceId':e['id'],'candidateDisplayName':label,
            'sourceUrl':url,'sourceProvider':e['provider'],
            'sourceExcerpt':str(e.get('summary') or '')[:400],
            'physicalAddress':None,'publicServiceContact':None,
            'registrationId':None,'licensedBusinessVerified':False,
            'officialRecordConfirmed':False,
            'status':'unverified_public_source_candidate'}

@router.get('/api/cases/{case_id}/business-leads')
def business_leads(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        rows=[dict(r) for r in conn.execute(
            "SELECT id,provider,label,summary,source_url,status FROM evidence WHERE case_id=? "
            "AND status!='rejected' ORDER BY fetched_at DESC,id DESC LIMIT 100",
            (case_id,))]
    # Business classification of person candidates is deliberately prohibited.
    items=[p for x in rows if (p:=_public_profile(x))] if case['subject_type']=='organization' else []
    return {'items':items,'businessRegistryReferences':REGISTRY_REFERENCE,
        'occupationRoutes':occupation_routes(case['query']),
        'independentLegalEntityVerification':False,
        'licensedPoiApiIntegrated':False,
        'notice':('Candidates are indexed source leads only, not verified businesses, '
                 'official registries or proof of service/contact ownership.')}

def bounded_alias_queries(original,aliases,*,include=False,limit=1):
    """Only analyst-entered, sourced spelling/transliteration hypotheses; no invented spellings."""
    if not include:return []
    original=' '.join(str(original or '').split()).casefold()
    variations=[]
    for x in aliases:
        value=' '.join(str(x.get('alias') or '').split())
        if not value or value.casefold()==original or len(value)>140:continue
        if x.get('alias_type') not in {'alternative_name','transliteration','former_name','brand'}:
            continue
        # A source URL is a provenance hint, NOT independent identity validation.
        if not str(x.get('source_url') or '').startswith('https://'):continue
        if value.casefold() not in {v.casefold() for v in variations}:variations.append(value)
        if len(variations)>=limit:break
    return variations
