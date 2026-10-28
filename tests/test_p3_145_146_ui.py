"""P3-145/146: explicit reviewed case comparison and preview-first task batch."""
from pathlib import Path
def test_case_comparison_and_batch_ui():
    js=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    for x in ('case-compare-form','task-batch-form','/api/agency/reviewed-case-compare?',
              '/tasks/batch-preview','f.dataset.confirmed'):
        assert x in js
