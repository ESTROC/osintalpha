"""P1-097 PDF export executes in a bounded child process with no network-fetcher."""
import sys
from app import pdf_worker

def test_worker_rejects_oversized_html_without_launch(monkeypatch):
    def fail(*args,**kwargs):raise AssertionError('should not launch')
    monkeypatch.setattr(pdf_worker.subprocess,'run',fail)
    try:pdf_worker.render_report_in_subprocess('X'*(pdf_worker.MAX_HTML_BYTES+1))
    except ValueError:pass
    else:assert False

def test_pdf_subprocess_receives_only_minimal_environment(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','sentinel-never-forward')
    monkeypatch.setenv('DATABASE_URL','postgresql://private:secret@db.example/test')
    def fake(args,**opts):
        assert opts['timeout']<=18
        assert opts['input'].startswith(b'<h1>Test')
        assert 'GROQ_API_KEY' not in opts['env']
        assert 'DATABASE_URL' not in opts['env']
        class Result:returncode=0;stdout=b'%PDF-1.7\nexample'
        return Result()
    monkeypatch.setattr(pdf_worker.subprocess,'run',fake)
    assert pdf_worker.render_report_in_subprocess('<h1>Test</h1>').startswith(b'%PDF')

def test_pdf_endpoint_uses_worker_not_inprocess_weasyprint(client,auth,case,monkeypatch):
    monkeypatch.setattr(pdf_worker,'render_report_in_subprocess',lambda html:b'%PDF-1.7\nsynthetic')
    result=client.get(f'/api/cases/{case}/report.pdf')
    assert result.status_code==200,result.text
    assert result.content.startswith(b'%PDF-')
