"""Bounded per-case structured provider response reuse and actionable diagnostics.

Cache is not a distributed single-flight lock. Provider answers remain unverified
source leads, and returned cache entries do not count as fresh observations.
"""
from __future__ import annotations
import hashlib,json,os,time
from dataclasses import asdict
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from . import db,main as core
from .connectors import Evidence,CATALOG
router=APIRouter()
VERSION="structured-collector-v1"
TTL_SECONDS=180
ALLOWED={x.id for x in CATALOG}
RECOVERY={
 "github":"Check official public API quota or use saved source records.",
 "stackoverflow":"Retry later or review already saved public developer records.",
 "openalex":"Use Crossref publication leads; do not infer author identity.",
 "crossref":"Use OpenAlex publication metadata and verify the original publisher.",
 "gleif":"Review official GLEIF query manually; missing LEI is not negative proof.",
 "wikidata":"Check official Wikidata source directly; matched names remain candidates.",
 "wikipedia":"Use other public publication sources; review publisher context.",
 "gdelt":"Review saved news leads, original publisher and date.",
}
def classify_error(code=None,error_type=None,retry_after=None):
    if code in (401,403):
        category,recovery,retry="authorization_or_rights","Verify provider key, access permission and source terms.",False
    elif code==429:
        category,recovery,retry="rate_limited","Wait for provider quota reset; inspect saved sources.",True
    elif isinstance(code,int) and code>=500:
        category,recovery,retry="upstream_unavailable","Retry after provider recovery; use case-saved records.",True
    elif error_type in ("TimeoutException","ReadTimeout","ConnectTimeout","TimeoutError"):
        category,recovery,retry="timeout","Reduce query scope, retry later, or use saved results.",True
    elif code in (400,404,422):
        category,recovery,retry="invalid_or_missing_request","Review query shape, available endpoint and provider contract.",False
    else:
        category,recovery,retry="unknown_error","Inspect current source health and original source terms.",False
    try:wait=min(120,max(0,int(float(retry_after)))) if retry_after is not None else None
    except (ValueError,TypeError):wait=None
    return {"category":category,"retryable":retry,"retryAfterSeconds":wait if retry else None,
       "recovery":recovery,"rawErrorOrSecretIncluded":False}

def cache_key(case_id,provider,query,subject,locale="default"):
    raw=json.dumps([case_id,provider,query,subject,locale,VERSION],separators=(",",":"))
    return hashlib.sha256(raw.encode()).hexdigest()

async def cached_collection(case_id,provider,query,subject,*,runner,client=None,locale="default",force_refresh=False):
    if provider not in ALLOWED:
        return await runner(provider,query,subject,client)
    # Rights updates must override previously saved cache hits immediately.
    with db.connect() as policy_db:
        reviewed=policy_db.execute(
           "SELECT rights_status,permitted_uses FROM provider_terms_reviews WHERE provider=?",
           (provider,)).fetchone()
    if reviewed and (reviewed["rights_status"]=="restricted" or
        (reviewed["rights_status"]=="approved_limited" and
         "live_queries" not in reviewed["permitted_uses"].split(","))):
        from .connectors import AdapterError
        raise AdapterError("Publisher use currently restricted; cached results cannot bypass source policy.")
    key=cache_key(case_id,provider,query,subject,locale)
    now=int(time.time())
    if not force_refresh:
        with db.connect() as conn:
            entry=conn.execute("SELECT result_json FROM provider_case_cache WHERE cache_key=? AND case_id=? AND expires_at>?",
                (key,case_id,now)).fetchone()
        if entry:
            try:
                obj=json.loads(entry["result_json"])
                return [Evidence(**x) for x in obj]
            except (ValueError,TypeError,KeyError):
                # Corrupt cached record is a miss, never a trusted response.
                pass
    result=await runner(provider,query,subject,client)
    try:
        if len(result)>100:return result
        saved=json.dumps([asdict(x) for x in result],ensure_ascii=False)
        if len(saved.encode())>320_000:return result
        with db.connect() as conn:
            conn.execute("DELETE FROM provider_case_cache WHERE cache_key=?",(key,))
            conn.execute("INSERT INTO provider_case_cache VALUES (?,?,?,?,?,?,?,?,?)",
                (key,case_id,provider,query,subject,VERSION,saved,now,now+TTL_SECONDS))
    except (ValueError,TypeError):
        return result
    return result

@router.get("/api/cases/{case_id}/provider-cache")
def cache_inventory(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        count=conn.execute("SELECT count(*) n FROM provider_case_cache WHERE case_id=? AND expires_at>?",
                          (case_id,int(time.time()))).fetchone()["n"]
    return {"cachedQueryVariants":count,"ttlSeconds":TTL_SECONDS,
        "vendorCallsAvoidedMeasured":None,
        "note":"Cached structured queries use exact case/provider/query/type/locale. Cache is not a distributed single-flight lock."}

@router.get("/api/research/provider-issues")
def provider_issues(actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        rows=[dict(x) for x in conn.execute(
            "SELECT provider,outcome,status_code,observed_at FROM provider_health_events "
            "ORDER BY observed_at DESC,id DESC LIMIT 1200")]
    items=[]
    for provider in sorted(ALLOWED):
        relevant=[x for x in rows if x["provider"]==provider]
        recent=relevant[0] if relevant else None
        success=next((x["observed_at"] for x in relevant if x["outcome"]=="ok"),None)
        items.append({"provider":provider,"lastObservedAt":recent["observed_at"] if recent else None,
            "lastStatusClass":classify_error(recent["status_code"])["category"] if recent and recent["outcome"]!="ok" else None,
            "lastSuccessAt":success,"currentStatus":"observed_error" if recent and recent["outcome"]!="ok" else "observed_ok" if recent else "unmeasured",
            "nextStep":RECOVERY.get(provider,"Review saved evidence and provider status."),
            "credentialValueIncluded":False,"uptimeVerified":False})
    return {"items":items,"notice":"Observations are not continuous probes; no provider secret or original query text is returned."}
