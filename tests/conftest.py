import os
import pytest
from fastapi.testclient import TestClient
from app.main import app, AUTH_TRIES

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('OSINTALPHA_DB_PATH',str(tmp_path/'test.db'))
    monkeypatch.setenv('OSINTALPHA_ADMIN_PASSWORD','AnIntentionallyLongTestPassword123')
    monkeypatch.delenv('XAI_API_KEY',raising=False)
    monkeypatch.delenv('TFL_APP_KEY',raising=False)
    AUTH_TRIES.clear()
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth(client):
    r=client.post('/api/auth/login',json={'username':'admin','password':'AnIntentionallyLongTestPassword123'})
    assert r.status_code==200
    return {'X-OSINT Alpha-Action':'1'}

@pytest.fixture
def case(client,auth):
    r=client.post('/api/cases',headers=auth,json={'title':'Authorized Example Research','subject_type':'person','query':'Test Person',
        'purpose':'Authorized professional qualifications research','authority_confirmed':True})
    assert r.status_code==201
    return r.json()['id']
