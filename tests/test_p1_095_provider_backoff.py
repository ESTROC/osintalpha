"""P1-095 bounded idempotent retries and no auth-rejection retries."""
import asyncio,httpx,pytest

from app.connectors import get_json,AdapterError

class Mocked:
    def __init__(self,statuses):self.statuses=statuses;self.calls=0
    async def get(self,url,params=None):
        self.calls+=1
        status=self.statuses[min(self.calls-1,len(self.statuses)-1)]
        req=httpx.Request('GET',url)
        res=httpx.Response(status,request=req,headers={'Retry-After':'0'})
        return res

def test_retry_one_rate_limit_then_succeed(monkeypatch):
    monkeypatch.setattr('asyncio.sleep',lambda seconds: _noop())
    client=Mocked([429,200])
    with pytest.raises(AdapterError,match='invalid JSON'):
        asyncio.run(get_json(client,'https://api.github.com/example'))
    assert client.calls==2

async def _noop():return None

def test_no_retry_403(monkeypatch):
    client=Mocked([403,200])
    with pytest.raises(AdapterError):asyncio.run(get_json(client,'https://api.github.com/example'))
    assert client.calls==1
