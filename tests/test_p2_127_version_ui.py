"""P2-127 health, authenticated UI version and operations must share release marker."""
from app.release import VERSION
def test_version_display_source_is_single_authoritative_value(client,auth):
    assert client.get("/api/auth/me").json()["releaseVersion"]==VERSION
    assert client.get("/api/health").json()["version"]==VERSION
    assert client.get("/api/research/ops-status").json()["version"]==VERSION
