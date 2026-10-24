import asyncio
import httpx
from app import main
from app.connectors import dns_records, internetdb, valid_domain, valid_public_ip, AdapterError

class Stub:
    async def get(self, url, params=None):
        if "dns.google" in url:
            typ=params["type"]
            answer={"A":[{"data":"93.184.215.14"}],"MX":[{"data":"10 mail.example.org."}],"NS":[{"data":"ns1.example.org."}]}[typ]
            return httpx.Response(200,request=httpx.Request("GET",url),json={"Status":0,"Answer":answer})
        if "internetdb.shodan.io" in url:
            return httpx.Response(200,request=httpx.Request("GET",url),json={"ip":"8.8.8.8","ports":[53,443],"vulns":["CVE-2020-1234"],"hostnames":["dns.google"],"tags":["cdn"],"cpes":[]})
        raise AssertionError("Unexpected external URL")

def test_target_validation():
    assert valid_domain("example.org")
    assert not valid_domain("http://example.org")
    assert not valid_domain("example.local")
    assert not valid_domain("localhost")
    assert valid_public_ip("8.8.8.8")
    assert not valid_public_ip("192.168.1.10")
    assert not valid_public_ip("127.0.0.1")

def test_domain_collector_returns_provenance():
    rows=asyncio.run(dns_records(Stub(),"example.org","domain"))
    assert {e.raw["recordType"] for e in rows} == {"A","MX","NS"}
    assert all(e.url.startswith("https://dns.google/") for e in rows)
    assert all("not establish domain ownership" in e.summary for e in rows)

def test_internetdb_passive_enrichment():
    rows=asyncio.run(internetdb(Stub(),"8.8.8.8","ip"))
    assert len(rows)==1
    assert rows[0].raw["mode"]=="passive"
    assert rows[0].raw["verified"] is False
    assert rows[0].raw["ports"]==[53,443]
    assert "never treat cve presence as verified vulnerability" in rows[0].summary.lower()
    try:
        asyncio.run(internetdb(Stub(),"10.0.0.8","ip"))
        assert False,"Expected AdapterError"
    except AdapterError:
        pass

def test_capabilities_and_auth(client,auth):
    assert client.get("/api/capabilities").status_code==200
    r=client.get("/api/capabilities").json()
    assert len(r["workflows"])==4
    assert {"domain","ip"} == {w["id"] for w in r["workflows"] if w["id"] in {"domain","ip"}}
    assert r["integratedSources"]>=9
    assert r["referencesOnly"]>=18

def test_domain_case_and_brief(client,auth):
    payload={"title":"Example domain review","subject_type":"domain","query":"example.org",
        "purpose":"Authorized demonstration of public DNS research",
        "authority_confirmed":True}
    assert client.post("/api/cases",headers=auth,json={**payload,"query":"https://example.org"}).status_code==422
    created=client.post("/api/cases",headers=auth,json=payload)
    assert created.status_code==201
    id=created.json()["id"]
    brief=client.get("/api/cases/"+id+"/brief")
    assert brief.status_code==200
    assert brief.json()["total"]==0
    assert any("source" in x.lower() for x in brief.json()["nextSteps"])
    assert client.get("/api/cases/"+id+"/brief").json()["subjectType"]=="domain"
    assert client.get("/api/cases/"+id+"/report.json").status_code==200

def test_private_ip_rejected(client,auth):
    payload={"title":"Private address review","subject_type":"ip","query":"192.168.0.1",
        "purpose":"Authorized network risk assessment of owned systems",
        "authority_confirmed":True}
    assert client.post("/api/cases",headers=auth,json=payload).status_code==422
    payload["query"]="8.8.8.8"
    assert client.post("/api/cases",headers=auth,json=payload).status_code==201

def test_domain_collect_mock(client,auth,monkeypatch):
    payload={"title":"DNS sample","subject_type":"domain","query":"example.org",
       "purpose":"Authorized test of public DNS source integration",
       "authority_confirmed":True}
    id=client.post("/api/cases",headers=auth,json=payload).json()["id"]
    async def fake(*args,**kwargs):
        from app.connectors import Evidence
        return [Evidence("A records · example.org","Public DNS answer","https://dns.google/query?name=example.org&type=A","domain:A",{"A":["93.184.215.14"]})]
    monkeypatch.setattr(main,"collect_one",fake)
    r=client.post("/api/cases/"+id+"/collect",headers=auth,json={"providers":["dns"]})
    assert r.status_code==200
    assert r.json()["results"][0]["new"]==1
    assert client.post("/api/cases/"+id+"/collect",headers=auth,json={"providers":["github"]}).status_code==422
    b=client.get("/api/cases/"+id+"/brief").json()
    assert b["total"]==1 and b["counts"]["candidate"]==1
    assert b["sourceStates"]["dns"]["state"]=="ok"
