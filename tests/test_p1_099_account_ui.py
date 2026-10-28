"""P1-099/101 role-appropriate UI and enforced password rotation path."""
from pathlib import Path

def test_browser_ui_has_password_rotation_and_forced_login_gate():
    s=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "function requiredPasswordChange()" in s
    assert "if(auth.mustChangePassword)" in s
    assert "if(s.user.must_change_password)" in s
    assert "credential-change-form" in s
    assert "data-admin-reset" in s and "data-admin-status" in s
