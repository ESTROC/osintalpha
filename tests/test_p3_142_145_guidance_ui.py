"""P3 142–145 case UI presents guidance, editable titles and reviewed case comparison."""
from pathlib import Path
def test_case_guidance_and_compare_html_ui():
    js=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert 'case-title-form' in js and 'case-compare-form' in js
    assert "s.outcomeGuidance=all.outcomeGuidance||null" in js
    assert 'Recommended next action' in js
    assert '/api/agency/compare-reviewed?left=' in js
