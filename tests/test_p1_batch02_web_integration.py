"""Integration checks: date metadata, official index scope, cited alias pass-through.
All external responses are synthetic, and no real people are investigated.
"""
import json
from app import v5,db

class FakeResponse:
    def raise_for_status(self):pass
    def json(self):
        return {'query':{'more_results_available':False},
                'web':{'results':[{'title':'Public notice',
                    'url':'https://example.org/public',
                    'description':'Index lead only',
                    'page_age':'2022-04-12',
                    'page_fetched':'2026-10-20T00:00:00Z'}]}}
class RecordingClient:
    captured=[]
    def __init__(self,*args,**kwargs):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*args):return False
    async def get(self,*args,**kwargs):
        self.captured.append(kwargs['params'])
        return FakeResponse()

def test_046_047_real_router_uses_historic_page_filter(client,auth,case,monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','synthetic-not-live')
    RecordingClient.captured=[]
    monkeypatch.setattr(v5.httpx,'AsyncClient',RecordingClient)
    res=client.post(f'/api/cases/{case}/web-discovery',headers=auth,json={
       'query':'Sample public notice in 2022',
       'consent':True,'depth':1,'pages':1,
       'date_from':'2022-01-01','date_to':'2022-12-31'})
    assert res.status_code==200,res.text
    assert RecordingClient.captured[0]['freshness']=='2022-01-01to2022-12-31'
    assert res.json()['pageDateWindow']['eventDateVerified'] is False
    with db.connect() as conn:
        row=conn.execute("SELECT raw_json FROM evidence WHERE case_id=? AND provider='brave_web'",(case,)).fetchone()
    raw=json.loads(row['raw_json'])
    assert raw['dateProvenance']['publisherPublicationDate'] is None
    assert raw['dateProvenance']['publisherEventDate'] is None
    assert raw['dateProvenance']['providerPageFetchedAt']=='2026-10-20T00:00:00Z'

def test_041_042_opted_in_alias_round_is_logged(client,auth,case,monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','synthetic-not-live')
    RecordingClient.captured=[]
    monkeypatch.setattr(v5.httpx,'AsyncClient',RecordingClient)
    added=client.post(f'/api/cases/{case}/aliases',headers=auth,json={
      'alias':'उदाहरण व्यक्ति','alias_type':'transliteration',
      'source_url':'https://example.org/notice',
      'rationale':'Recorded in public synthetic fixture'})
    assert added.status_code==201,added.text
    response=client.post(f'/api/cases/{case}/web-discovery',headers=auth,json={
      'consent':True,'depth':1,'include_sourced_aliases':True})
    assert response.status_code==200,response.text
    assert response.json()['sourcedAliasesRequested'] is True
    assert not response.json()['sourcedAliasProvenIdentity']
    assert any('उदाहरण व्यक्ति' in params['q'] for params in RecordingClient.captured)
