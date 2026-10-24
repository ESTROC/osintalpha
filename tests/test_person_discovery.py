
import asyncio
import httpx
from app.connectors import github, stackoverflow

def make_response(url, data, status=200):
    return httpx.Response(status,request=httpx.Request('GET',url),json=data)

class GitHubStub:
    def __init__(self):self.calls=[]
    async def get(self,url,params=None):
        self.calls.append((url,params))
        if url.endswith('/search/users'):
            assert params['q']=='Ayush Tripathi in:name type:user'
            return make_response(url, {'items':[{'login':'ayush-example','id':120,'type':'User'}]})
        if url.endswith('/users/ayush-example'):
            return make_response(url,{'name':'Ayush Tripathi','bio':'Public software engineering portfolio',
              'location':'Delhi','company':None,'public_repos':12})
        raise AssertionError(f'Unexpected call {url}')

def test_github_person_name_query_and_richer_public_profile():
    stub=GitHubStub()
    result=asyncio.run(github(stub,'Ayush Tripathi','person'))
    assert len(result)==1
    assert result[0].label=='Ayush Tripathi'
    assert 'Public software engineering portfolio' in result[0].summary
    assert 'No ownership or identity match' in result[0].summary
    assert result[0].url=='https://github.com/ayush-example'

class GitHubFallbackStub:
    async def get(self,url,params=None):
        if url.endswith('/search/users'):
            if 'in:name' in params['q']:
                return make_response(url,{'items':[]})
            assert params['q']=='AyushTripathi in:login type:user'
            return make_response(url,{'items':[{'login':'AyushTripathi','id':88}]})
        return make_response(url,{'name':None,'public_repos':5})

def test_github_username_fallback_if_display_name_absent():
    result=asyncio.run(github(GitHubFallbackStub(),'Ayush Tripathi','person'))
    assert len(result)==1
    assert result[0].raw['login']=='AyushTripathi'

class StackExchangeStub:
    async def get(self,url,params=None):
        assert url=='https://api.stackexchange.com/2.3/users'
        assert params['inname']=='Ayush Tripathi'
        return make_response(url,{'items':[
            {'display_name':'Ayush Tripathi','user_id':55,'reputation':145,'location':'Delhi'},
            {'display_name':'Ayush Singh','user_id':56,'reputation':180},
            {'display_name':'Tripathi Ayush','user_id':57,'reputation':22}
        ]})

def test_stackoverflow_exact_tokens_and_namesake_safety():
    r=asyncio.run(stackoverflow(StackExchangeStub(),'Ayush Tripathi','person'))
    assert len(r)==2
    assert all(x.raw['identity_verified'] is False for x in r)
    assert all('identity' in x.summary.lower() for x in r)
    assert all(x.url.startswith('https://stackoverflow.com/users/') for x in r)
