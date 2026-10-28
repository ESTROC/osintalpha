"""P1 065/066: bounded binary intake; no arbitrary fetch or authenticity claim."""
import base64,hashlib,io
from app.source_archives import decode_asset,MAX_ASSET
from fastapi import HTTPException
import pytest

def _png():
    # Header plus opaque example bytes; no image decode required.
    return b'\x89PNG\r\n\x1a\n'+b'example-test-evidence'*8

def test_066_explicit_rights_and_archive_integrity(client,auth,case):
    ev=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Synthetic PNG published visual','summary':'Manual media provenance',
        'source_url':'https://example.org/visual'}).json()['id']
    content=_png()
    data={'evidence_url':'https://example.org/visual',
          'asset_kind':'png','content_base64':base64.b64encode(content).decode(),
          'rights_confirmed':False,'retention_days':1}
    path=f'/api/cases/{case}/evidence/{ev}/source-artifacts'
    assert client.post(path,headers=auth,json=data).status_code==422
    data['rights_confirmed']=True
    item=client.post(path,headers=auth,json=data)
    assert item.status_code==201,item.text
    assert item.json()['originalSha256']==hashlib.sha256(content).hexdigest()
    assert item.json()['textExtracted'] is False
    aid=item.json()['id']
    listed=client.get(f'/api/cases/{case}/source-artifacts').json()
    assert listed['items'][0]['id']==aid
    fetched=client.get(f'/api/cases/{case}/source-artifacts/{aid}/original')
    assert fetched.status_code==200
    assert fetched.content==content
    assert fetched.headers['content-type']=='application/octet-stream'
    erased=client.delete(f'/api/cases/{case}/source-artifacts/{aid}',headers=auth)
    assert erased.status_code==200
    assert not erased.json()['backupErasureVerified']
    assert client.get(f'/api/cases/{case}/source-artifacts/{aid}/original').status_code==404

def test_065_invalid_pdf_and_wrong_provenance_fail(client,auth,case):
    ev=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
        'label':'Synthetic public PDF','summary':'Not actually a PDF',
        'source_url':'https://example.org/public.pdf'}).json()['id']
    path=f'/api/cases/{case}/evidence/{ev}/source-artifacts'
    data={'evidence_url':'https://example.org/public.pdf',
          'asset_kind':'pdf','content_base64':base64.b64encode(_png()).decode(),
          'rights_confirmed':True}
    assert client.post(path,headers=auth,json=data).status_code==422
    data['asset_kind']='png';data['evidence_url']='https://example.org/mismatch'
    assert client.post(path,headers=auth,json=data).status_code==422

def test_065_parser_bounded_and_signatures():
    with pytest.raises(HTTPException):decode_asset(base64.b64encode(b'NOT_A_PDF'*10).decode(),'pdf')
    with pytest.raises(HTTPException):decode_asset(base64.b64encode(b'WARC/1.0\r\n' + b'x'*200001).decode(),'warc')
