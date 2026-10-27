"""P0 report continuity: saved original question and clearly unapproved AI text."""
from html.parser import HTMLParser


def test_research_question_and_unverified_chat_survive_report_export(client,auth):
    q='Review synthetic records for Example Bicycle Cooperative'
    a=client.post('/api/search/start',headers=auth,json={
        'question':q,'purpose':'Authorized synthetic source-citation validation',
        'authority_confirmed':True})
    assert a.status_code==201,a.text
    cid=a.json()['id']
    chat=client.post(f'/api/cases/{cid}/chat',headers=auth,json={
        'provider':'local','question':'What remains unverified?'
    })
    assert chat.status_code==200,chat.text
    report=client.get(f'/api/cases/{cid}/report.html')
    assert report.status_code==200,report.text
    assert q in report.text
    assert 'UNVERIFIED AI SYNTHESIS' in report.text
    assert 'not an approved factual assessment' in report.text
    assert chat.json()['answer'][:30] in report.text
    assert 'Candidate matches are not confirmed identities' in report.text


def test_report_escapes_saved_untrusted_search_question(client,auth):
    q='Official source for <script>alert(1)</script> public company'
    a=client.post('/api/search/start',headers=auth,json={
        'question':q,'purpose':'Authorized synthetic XSS escape validation',
        'authority_confirmed':True})
    assert a.status_code==201,a.text
    report=client.get(f"/api/cases/{a.json()['id']}/report.html")
    assert report.status_code==200
    assert '<script>alert(1)</script>' not in report.text
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in report.text
