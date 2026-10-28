"""P2 126–128 one release truth, no silent unsupported model and private keys."""
from pathlib import Path
import pytest
from fastapi import HTTPException
from app.release import VERSION, configured_groq_model,model_manifest
from app.main import app
ROOT=Path(__file__).resolve().parents[1]

def test_manifest_and_api_version_remain_aligned(client):
    assert app.version==VERSION
    assert client.get("/api/health").json()["version"]==VERSION
    with open(ROOT/"README.md") as f:assert VERSION in f.read()
    with open(ROOT/".env.example") as f:
        text=f.read()
        assert "BRAVE_SEARCH_API_KEY=" in text
        assert "GROQ_API_KEY=" in text
        assert "GROQ_MODEL=" in text
    blueprint=(ROOT/"render.yaml").read_text()
    assert "BRAVE_SEARCH_API_KEY" in blueprint
    assert "GROQ_API_KEY" in blueprint

def test_unknown_groq_model_blocked_before_remote_call(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL","unsupported/unregistered-model")
    assert model_manifest()["supported"] is False
    with pytest.raises(HTTPException) as exc:configured_groq_model()
    assert exc.value.status_code==409
    assert "local" in model_manifest()["fallback"].lower()

def test_allowed_groq_request_modes_are_explicit(monkeypatch):
    for candidate in ("openai/gpt-oss-20b","openai/gpt-oss-120b"):
        monkeypatch.setenv("GROQ_MODEL",candidate)
        assert configured_groq_model()==candidate
        assert model_manifest()["modes"]["json_schema"]
        assert model_manifest()["modes"]["browser_search"]
    assert model_manifest()["vendorModelAvailabilityVerified"] is False
