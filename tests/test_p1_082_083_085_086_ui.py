"""UI acceptance assertions for main-case dossier and task-oriented navigation."""
from pathlib import Path

def test_082_overview_is_answer_first():
    source=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "return header+caseDossier()+context" in source
    assert 'CASE ANSWER · PROVENANCE FIRST' in source
    assert 'Contradictions and missing information' in source
    assert "const tabs=['overview','assistant','evidence','reports']" in source

def test_083_other_platform_tools_are_progressively_hidden_in_case():
    source=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "s.where==='case'?'<details class=" in source
    assert 'Other workspaces' in source

def test_085_claim_drilldown_and_record_citations():
    source=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert 'data-explain-claim' in source
    assert '/claims/' in source and '/explain' in source
    assert 'Saved source and provider trace' in source

def test_086_visible_filter_choices():
    source=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    for key in ('dossier-sort','dossier-status','dossier-class'):
        assert key in source

def test_084_licensed_thumbnail_has_nonidentity_alt():
    source=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert 'Licensed publisher source media; not a verified person photograph' in source
