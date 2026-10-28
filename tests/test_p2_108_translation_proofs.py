"""P2-108: non-English source quotation survives and is offset-validated."""
import hashlib
from app import db

def test_translation_preserves_original_offsets_and_sha(client,auth,case):
    ev=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
       'label':'Synthetic Hindi article','summary':'Licensed synthetic source for review',
       'source_url':'https://example.org/public-research'})
    assert ev.status_code==200,ev.text
    id=ev.json()['id']
    original='यह एक सार्वजनिक अनुसंधान घोषणा है।'
    sha=hashlib.sha256(original.encode()).hexdigest()
    with db.connect() as c:
        c.execute('INSERT INTO source_captures VALUES (?,?,?,?,?,?,?,?,?,?)',
            ('hi-test-cap',case,id,'https://example.org/public-research',
             'text/plain',original,sha,'2026-10-28T00:00:00Z','captured',''))
    body={'evidence_id':id,'capture_id':'hi-test-cap','source_start':0,
      'source_end':len(original),'original_text':original,'translated_text':
      'This is a public research announcement.','language_from':'hi','language_to':'en',
      'method':'human_attested','reviewer_note':'Synthetic translation attested by analyst for testing only.',
      'rights_confirmed':True}
    bad=client.post(f'/api/cases/{case}/captured-translations',headers=auth,
       json={**body,'original_text':'Different source text'})
    assert bad.status_code==422
    good=client.post(f'/api/cases/{case}/captured-translations',headers=auth,json=body)
    assert good.status_code==201,good.text
    assert good.json()['sourceSha256']==sha
    assert not good.json()['machineOcrPerformed']
    listing=client.get(f'/api/cases/{case}/captured-translations')
    assert listing.status_code==200,listing.text
    assert listing.json()['items'][0]['original_text']==original
    assert listing.json()['items'][0]['source_start']==0
