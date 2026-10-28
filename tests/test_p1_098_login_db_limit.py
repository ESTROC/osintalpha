"""P1 098 durable per-account/per-socket-peer password guessing limits."""
from app import db
from app.main import AUTH_TRIES

def test_failed_attempts_survive_memory_reset_and_ignore_forwarded_ip(client):
    for i in range(8):
        res=client.post('/api/auth/login',json={'username':'admin','password':'wrong'},
            headers={'X-Forwarded-For':f'1.2.3.{i}','X-Real-IP':f'1.2.3.{i}'})
        assert res.status_code==401,res.text
    AUTH_TRIES.clear()
    response=client.post('/api/auth/login',
      json={'username':'admin','password':'AnIntentionallyLongTestPassword123'},
      headers={'X-Forwarded-For':'198.51.100.99'})
    assert response.status_code==429
    with db.connect() as c:
        assert c.execute('SELECT count(*) n FROM auth_failed_attempts').fetchone()['n']==8

def test_success_clears_same_account_peer_only(client):
    fail=client.post('/api/auth/login',json={'username':'admin','password':'incorrect'})
    assert fail.status_code==401
    yes=client.post('/api/auth/login',json={'username':'admin','password':'AnIntentionallyLongTestPassword123'})
    assert yes.status_code==200
    with db.connect() as c:
        assert c.execute('SELECT count(*) n FROM auth_failed_attempts').fetchone()['n']==0

def test_username_enumeration_does_not_reset_socket_peer_limit(client):
    for n in range(8):
        r=client.post('/api/auth/login',json={'username':'fakeuser'+str(n),'password':'invalid'})
        assert r.status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'AnIntentionallyLongTestPassword123'}).status_code==429
