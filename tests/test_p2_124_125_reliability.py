"""P2-124/125 classify provider failures and reuse only matching authorized case cache."""
import asyncio
from app.connectors import Evidence
from app.provider_reliability import classify_error,cached_collection

def test_http_categories_hide_creds():
    assert classify_error(401)["category"]=="authorization_or_rights"
    assert classify_error(403)["retryable"] is False
    assert classify_error(429,retry_after="20")["retryAfterSeconds"]==20
    assert classify_error(503)["retryable"] is True
    assert classify_error(error_type="TimeoutException")["category"]=="timeout"
    assert not classify_error(500)["rawErrorOrSecretIncluded"]

def test_same_case_cache_hit_different_case_miss_and_forced_refresh(client,auth,case):
    calls=[]
    async def runner(provider,query,subject,remote):
        calls.append((provider,query))
        return [Evidence("Synthetic author","Public candidate only","https://example.org/public",
                         "public-ref",{"source":"synthetic"},None)]
    def call(c,refresh=False):
        return asyncio.run(cached_collection(c,"crossref","synthetic academic", "person",
                runner=runner,force_refresh=refresh))
    assert call(case)[0].label=="Synthetic author"
    assert call(case)[0].label=="Synthetic author"
    assert len(calls)==1
    assert call(case,True)
    assert len(calls)==2
    another=client.post("/api/cases",headers=auth,json={
      "title":"Separate Synthetic","subject_type":"person","query":"Demo Person",
      "purpose":"Authorized synthetic publication source comparison",
      "authority_confirmed":True}).json()["id"]
    assert call(another)
    assert len(calls)==3
    inv=client.get(f"/api/cases/{case}/provider-cache")
    assert inv.status_code==200 and inv.json()["cachedQueryVariants"]==1

def test_provider_diagnostics_no_sensitive_terms(client,auth):
    output=client.get("/api/research/provider-issues")
    assert output.status_code==200,output.text
    assert all(x["credentialValueIncluded"] is False for x in output.json()["items"])


def test_provider_rights_update_invalidates_cached_read(client,auth,case):
    import pytest
    from app import db
    from app.connectors import AdapterError
    async def runner(provider,query,subject,remote):
        return [Evidence("Public organization record","Synthetic candidate only",
             "https://example.org/public","entity-1",{"id":7},None)]
    asyncio.run(cached_collection(case,"gleif","Test Example","organization",runner=runner))
    with db.connect() as conn:
        owner=conn.execute("SELECT created_by FROM cases WHERE id=?",(case,)).fetchone()["created_by"]
        conn.execute("INSERT INTO provider_terms_reviews VALUES (?,?,?,?,?,?,?)",
          ("gleif","restricted","","https://example.org/terms",
           "Synthetic temporary restricted licensing for test",owner,"2026-10-29T00:00:00Z"))
    with pytest.raises(AdapterError,match="restricted"):
        asyncio.run(cached_collection(case,"gleif","Test Example","organization",runner=runner))
