from pathlib import Path
def test_answer_first_and_accessible_provider_badges():
    s=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "const sourceBadge=" in s and "sourceBadge(x.provider)" in s
    assert "return main+missing+sourcePanel+" in s
    assert 'Licensed publisher source media; not a verified person photograph' in s
