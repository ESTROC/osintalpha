"""Bounded subprocess PDF export. No queue or isolated production worker yet."""
from __future__ import annotations
import os,subprocess,sys
from pathlib import Path

MAX_HTML_BYTES=450_000
MAX_PDF_BYTES=9_000_000

def render_report_in_subprocess(html):
    data=str(html).encode('utf-8')
    if not data or len(data)>MAX_HTML_BYTES:
        raise ValueError('HTML document exceeds bounded export size.')
    root=str(Path(__file__).resolve().parent.parent)
    # Do not transmit DB passwords or model API keys into the rendering child.
    safe_env={'PATH':os.getenv('PATH','/usr/bin:/bin'),
              'PYTHONPATH':root,'PYTHONIOENCODING':'utf-8',
              'HOME':'/tmp','LANG':'C.UTF-8'}
    try:
        r=subprocess.run([sys.executable,'-m','app.pdf_worker','--child'],input=data,
          capture_output=True,timeout=18,cwd=root,env=safe_env,check=False)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError('PDF export worker exceeded deadline.') from exc
    if r.returncode!=0 or not r.stdout.startswith(b'%PDF-') or len(r.stdout)>MAX_PDF_BYTES:
        raise RuntimeError('PDF export failed resource or output verification.')
    return r.stdout

def _child():
    import resource
    try:
        resource.setrlimit(resource.RLIMIT_CPU,(12,13))
        resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_PDF_BYTES,MAX_PDF_BYTES))
    except (ValueError,OSError):
        pass
    original=sys.stdin.buffer.read(MAX_HTML_BYTES+1)
    if len(original)>MAX_HTML_BYTES:return 4
    from weasyprint import HTML
    def block_network(url,*args,**kwargs):
        raise ValueError('External URL loading prohibited in PDF render.')
    output=HTML(string=original.decode('utf-8'),url_fetcher=block_network).write_pdf()
    if len(output)>MAX_PDF_BYTES:return 5
    sys.stdout.buffer.write(output)
    return 0

if __name__=='__main__' and '--child' in sys.argv:
    sys.exit(_child())
