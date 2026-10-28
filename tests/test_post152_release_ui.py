"""Post-152 Settings uses explicit administrator-only review UX."""
from pathlib import Path

def test_governance_settings_link_and_access():
    js=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "function releaseReadinessPanel()" in js
    assert "s.user?.role!=='admin'" in js
    assert "data-check-readiness" in js
    assert "/api/admin/release-readiness" in js
    assert "Regulated production: NOT APPROVED." in js
