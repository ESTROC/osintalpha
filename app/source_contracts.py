"""Source-owned adapters for local licensed data, not upstream engines.

All returned identity/entity labels remain analyst hypotheses. This module never
spins up OpenAleph/FTM, OpenCTI, IntelOwl, ArchiveBox or network replay.
"""
from __future__ import annotations
import base64, hashlib, hmac, json, re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from . import db
from . import main as core

router = APIRouter()
ENTITY_TYPES = {"Organization", "Company", "PublicBody"}
TIMESTAMP_KEYS = {
    "published": ("datePublished", "published", "publication_date", "published_at"),
    "updated": ("dateModified", "updated", "last_modified", "updated_at"),
    "language": ("inLanguage", "language", "lang"),
}

def official_https(raw: str) -> bool:
    from .v5 import public_https
    return bool(public_https(raw))

class EntityCrosswalk(BaseModel):
    external_id: str = Field(min_length=4,max_length=100,pattern=r"^[A-Za-z0-9_./:-]+$")
    entity_type: Literal["Organization","Company","PublicBody"]
    name: str = Field(min_length=3,max_length=160)
    source_url: str = Field(min_length=12,max_length=550)
    source_rights_reference: str = Field(min_length=12,max_length=550)
    source_license_reviewed: bool = False
    source_summary: str = Field(min_length=20,max_length=480)

@router.post("/api/cases/{case_id}/schema-entity-import",status_code=201)
def source_entity_import(case_id:str,body:EntityCrosswalk,actor=Depends(core.protect)):
    if not body.source_license_reviewed:
        raise HTTPException(422,"Administrator must confirm this source's right to limited storage.")
    if not official_https(body.source_url) or not official_https(body.source_rights_reference):
        raise HTTPException(422,"An HTTPS original and publisher rights URL are required.")
    canonical=json.dumps({"source":body.source_url,"id":body.external_id,
        "type":body.entity_type,"name":body.name},sort_keys=True)
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        if case["subject_type"]!="organization":
            raise HTTPException(422,"Source entity import supports organization investigations only.")
        existing=conn.execute("SELECT id FROM evidence WHERE case_id=? AND provider=? AND source_ref=?",
           (case_id,"typed_entity_import",body.external_id)).fetchone()
        if existing:raise HTTPException(409,"This case already contains that external entity ID.")
        eid=core.uid()
        payload=json.dumps({"externalEntityId":body.external_id,"entityType":body.entity_type,
             "originalUrl":body.source_url,"rightsReference":body.source_rights_reference,
             "format":"local_ftm_like_crosswalk_v1","notUpstreamFtM":True},sort_keys=True)
        conn.execute("""INSERT INTO evidence(id,case_id,provider,label,summary,source_url,source_ref,
                      fetched_at,observed_at,sha256,raw_json)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
           (eid,case_id,"typed_entity_import",body.name,body.source_summary,body.source_url,
            body.external_id,core.iso_now(),None,digest,payload))
    core.write_audit(actor["id"],"typed_entity_import","case",case_id,eid)
    return {"evidenceId":eid,"sourceDigest":digest,"reviewState":"candidate",
       "upstreamEngineConnected":False,"independentlyVerifiedEntity":False}

@router.get("/api/cases/{case_id}/schema-entity-export")
def source_entity_export(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
            "SELECT id,label,summary,source_url,source_ref,raw_json,status,sha256 "
            "FROM evidence WHERE case_id=? AND provider=? ORDER BY id LIMIT 200",
            (case_id,"typed_entity_import"))]
    records=[]
    for x in rows:
        raw=json.loads(x["raw_json"])
        records.append({"id":x["source_ref"],"schema":raw["entityType"],
           "properties":{"name":[x["label"]]},"evidenceId":x["id"],
           "provenance":{"url":x["source_url"],"rightsUrl":raw["rightsReference"],
           "captureHash":x["sha256"],"status":x["status"]}})
    return {"schemaProfile":"local_ftm_like_crosswalk_v1","entities":records,
       "fullFollowTheMoneySchema":False,"upstreamOpenAlephConnected":False,
       "warning":"Mapping is a local limited crosswalk; no full FTM schema validation or external entity reconciliation."}

@router.get("/api/cases/{case_id}/defensive-bridge")
def defensive_bridge(case_id:str,provider:Literal["opencti","intelowl"],actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
    if case["subject_type"] not in ("domain","ip"):
        raise HTTPException(422,"Defensive threat connector restricted to domains or public IPs.")
    return {"provider":provider,"subject":case["query"],"providerInstalled":False,
       "remoteCallsMade":0,"enabled":False,"noPersonLookup":True,
       "requires":["legal_rights_review","separate_service_credentials","approved_connector",
                   "fixed_host_scopes","defensive_authorization"],
       "fallback":"Use the existing authorized passive DNS / InternetDB source collectors."}

def parse_utc(raw):
    if not isinstance(raw,str) or not raw.strip():return None
    try:
        s=raw.strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2}))?",s):
            return None
        if len(s)==10:
            datetime.strptime(s,"%Y-%m-%d")
            return {"value":s,"precision":"date","timezone":None}
        dt=datetime.fromisoformat(s.replace("Z","+00:00"))
        return {"value":s,"precision":"seconds","timezone":str(dt.tzinfo)}
    except ValueError:return None

def first_valid(raw,aliases):
    for name in aliases:
        val=raw.get(name)
        if isinstance(val,str) and val.strip():
            return val.strip()[:120],name
    return None,None

@router.get("/api/cases/{case_id}/source-metadata")
def source_metadata(case_id:str,limit:int=Query(50,ge=1,le=150),actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
          "SELECT id,provider,source_url,raw_json,observed_at,fetched_at,reviewed_at "
          "FROM evidence WHERE case_id=? ORDER BY fetched_at DESC,id DESC LIMIT ?",(case_id,limit))]
    items=[]
    for row in rows:
        try:raw=json.loads(row["raw_json"] or "{}")
        except (ValueError,TypeError):raw={}
        if not isinstance(raw,dict):raw={}
        published,publisher_key=first_valid(raw,TIMESTAMP_KEYS["published"])
        updated,updated_key=first_valid(raw,TIMESTAMP_KEYS["updated"])
        lang,lang_key=first_valid(raw,TIMESTAMP_KEYS["language"])
        if not lang or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?",lang):lang=None;lang_key=None
        items.append({"evidenceId":row["id"],"provider":row["provider"],
            "originalUrl":row["source_url"],"language":lang,"languageBasis":lang_key,
            "publishedAt":parse_utc(published),"publishedFromField":publisher_key,
            "updatedAt":parse_utc(updated),"updatedFromField":updated_key,
            "firstSeenAt":None,"sourceObservedAt":parse_utc(row["observed_at"]),
            "fetchedAt":parse_utc(row["fetched_at"]),
            "reviewedAt":parse_utc(row["reviewed_at"]),
            "publicationInventedFromFetch":False})
    return {"items":items,"completeInventory":len(rows)<limit,
       "notice":"Missing publication/updated/first-seen dates stay null. Fetched time is not a published/event date."}

@router.get("/api/cases/{case_id}/warc-inspection/{artifact_id}")
def warc_inspection(case_id:str,artifact_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        item=conn.execute("SELECT asset_kind,original_sha256,content_b64,original_url,expires_at "
             "FROM source_document_archives WHERE case_id=? AND id=?",(case_id,artifact_id)).fetchone()
    if not item or item["asset_kind"]!="warc":
        raise HTTPException(404,"Authorized WARC source artifact not found.")
    from datetime import datetime,timezone
    if datetime.fromisoformat(item["expires_at"])<=datetime.now(timezone.utc):
        raise HTTPException(410,"Original artifact retention expired.")
    try:blob=base64.b64decode(item["content_b64"],validate=True)
    except ValueError as exc:raise HTTPException(409,"Invalid retained archive bytes.") from exc
    digest=hashlib.sha256(blob).hexdigest()
    if not hmac.compare_digest(digest,item["original_sha256"]):
        raise HTTPException(409,"WARC original integrity mismatch.")
    if not blob.startswith((b"WARC/1.0\r\n",b"WARC/1.1\r\n")):
        raise HTTPException(409,"Unknown original WARC signature.")
    return {"artifactId":artifact_id,"originalUrl":item["original_url"],
        "originalSha256":digest,"byteCount":len(blob),"format":"WARC",
        "replayEnabled":False,"publisherIdentityVerified":False,
        "notice":"Hash and header verified for manually supplied archive. No ArchiveBox capture or pywb replay service installed."}
