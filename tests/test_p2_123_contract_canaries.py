"""P2-123 consented provider canary records structured outcomes, not personal queries."""
from app.connectors import Evidence

def test_consent_canary_record_no_secret_query(client,auth,monkeypatch):
    async def fake(provider,query,subject):
        assert provider=="github"
        return [Evidence("Synthetic result","Official schema smoke",
            "https://github.com/octocat","octocat",{"id":42},None)]
    monkeypatch.setattr("app.connectors.collect_one",fake)
    r=client.post("/api/research/provider-canary",headers=auth,json={"provider":"github","consent":False})
    assert r.status_code==422
    r=client.post("/api/research/provider-canary",headers=auth,json={"provider":"github","consent":True})
    assert r.status_code==200,r.text
    assert r.json()["classification"]=="compatible_response"
    out=client.get("/api/research/provider-canary-history")
    assert out.status_code==200,out.text
    assert out.json()["items"][0]["provider"]=="github"
    assert "octocat" not in str(out.json()["items"])
    assert out.json()["scheduledLiveChecks"] is False
