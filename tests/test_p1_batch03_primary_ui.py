"""Frontend integration: candidate comparison shown in primary results, not only advanced."""
from pathlib import Path

def test_055_case_overview_mentions_side_by_side_namesake_review():
    source=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert 'Distinct candidate identities · compare before linking' in source
    assert 'No identity verified by display name or shared username.' in source
    assert 'Review candidate evidence' in source
    assert 'What remains unverified?' in source
