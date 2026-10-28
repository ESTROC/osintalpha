"""P2 119–122: source-owned typed crosswalk, safe unavailable bridges and honest dates."""
import json,hashlib
from app import db

def test_crosswalk_requires_rights_and_is_case_scoped(client,auth):
    case=client.post("/api/cases",headers=auth,json={
      "title":"Synthetic Public Entity","subject_type":"organization","query":"Example Public Body",
      "purpose":"Review synthetic licensed public entity mapping","authority_confirmed":True}).json()["id"]
    body={"external_id":"ex:ORG-15","entity_type":"Organization","name":"Example Public Body",
          "source_url":"https://example.org/source","source_rights_reference":"https://example.org/terms",
          "source_summary":"Synthetic licensed local source reference only.","source_license_reviewed":False}
    path=f"/api/cases/{case}/schema-entity-import"
    assert client.post(path,headers=auth,json=body).status_code==422
    body["source_license_reviewed"]=True
    r=client.post(path,headers=auth,json=body)
    assert r.status_code==201,r.text
    assert r.json()["reviewState"]=="candidate"
    assert client.post(path,headers=auth,json=body).status_code==409
    out=client.get(f"/api/cases/{case}/schema-entity-export")
    assert out.status_code==200,out.text
    assert out.json()["entities"][0]["id"]=="ex:ORG-15"
    assert not out.json()["fullFollowTheMoneySchema"]

def test_domain_bridge_disabled_until_approved(client,auth,case):
    assert client.get(f"/api/cases/{case}/defensive-bridge?provider=intelowl").status_code==422
    domain=client.post("/api/cases",headers=auth,json={
      "title":"Synthetic domain","subject_type":"domain","query":"example.org",
      "purpose":"Authorized defensive passive DNS check","authority_confirmed":True}).json()["id"]
    out=client.get(f"/api/cases/{domain}/defensive-bridge?provider=opencti")
    assert out.status_code==200
    assert out.json()["remoteCallsMade"]==0
    assert not out.json()["providerInstalled"]

def test_publisher_metadata_missing_dates_do_not_inherit_fetch(client,auth,case):
    r=client.post(f"/api/cases/{case}/evidence",headers=auth,json={
       "label":"Synthetic research","summary":"Public research index only",
       "source_url":"https://example.org/page"})
    assert r.status_code==200,r.text
    out=client.get(f"/api/cases/{case}/source-metadata")
    assert out.status_code==200,out.text
    row=out.json()["items"][0]
    assert row["publishedAt"] is None and row["updatedAt"] is None
    assert row["fetchedAt"] is not None
    assert row["publicationInventedFromFetch"] is False
