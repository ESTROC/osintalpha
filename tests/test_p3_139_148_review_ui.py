"""P3-139/143/144/147/148: reviewer UI, redaction preview and concise title edit."""
from pathlib import Path
def test_report_review_forms_and_bounded_source_display():
    s=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    for field in ('distribution-approval-form','report-redaction-form','case-title-form'):
        assert field in s
    assert "'distribution/preview'" in s and "'research-next-step'" in s
    assert 'Full original question retained' in s
    assert 'Approval is revoked automatically' in s
