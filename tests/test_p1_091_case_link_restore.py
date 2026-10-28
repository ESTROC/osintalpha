"""P1 078/091: refresh from an authorized case link restores case rather than resetting home."""
from pathlib import Path

def test_case_deep_link_restoration():
    js=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "new URLSearchParams(window.location.search).get('case')" in js
    assert "window.history.replaceState(null,'','/?case='+encodeURIComponent(id))" in js
    assert "if(fromUrl&&/^[a-f0-9]{24}$/.test(fromUrl))" in js
