"""New activity UI uses real case-scoped chronology and signed cursor paging."""
from pathlib import Path

def test_activity_controls_and_auth_endpoints():
    s=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "activity:['search-history','changes','research-history','chronology','evidence-cursor','source-origin-review','review-obligations']" in s
    assert 'data-load-cursor' in s and 'data-run-evolution' in s
    assert '/run-source-evolution?older_run=' in s
    assert 'Event dates are not retrieval dates' in s
    assert 'newerCapturedAt' in s
