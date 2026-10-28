"""P1 099–101: rotation, forced expiry, immediate session revocation and admin-only controls."""
def create_analyst(client,auth,username='rotationuser'):
    r=client.post('/api/users',headers=auth,json={'username':username,
       'password':'InitialTestCredential2026!','role':'analyst'})
    assert r.status_code==201,r.text
    return r.json()['id']

def test_self_change_revokes_all_sessions(client,auth):
    uid=create_analyst(client,auth)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as other:
        signin=other.post('/api/auth/login',json={'username':'rotationuser','password':'InitialTestCredential2026!'})
        assert signin.status_code==200,signin.text
        old=other.get('/api/auth/me')
        assert old.status_code==200
        rotated=other.post('/api/auth/change-password',headers=auth,json={
          'current_password':'InitialTestCredential2026!','new_password':'StrongerRotatedCredential2026!'})
        assert rotated.status_code==200,rotated.text
        assert other.get('/api/auth/me').status_code==401
        assert other.post('/api/auth/login',json={'username':'rotationuser','password':'InitialTestCredential2026!'}).status_code==401
        assert other.post('/api/auth/login',json={'username':'rotationuser','password':'StrongerRotatedCredential2026!'}).status_code==200

def test_admin_reset_forces_rotation_and_disable_revokes(client,auth):
    uid=create_analyst(client,auth,'forceduser')
    r=client.post(f'/api/users/{uid}/reset-credential',headers=auth,json={
       'administrator_password':'AnIntentionallyLongTestPassword123',
       'temporary_password':'ForcedTemporaryCredential2026!'})
    assert r.status_code==200,r.text
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as user:
        assert user.post('/api/auth/login',json={'username':'forceduser','password':'ForcedTemporaryCredential2026!'}).status_code==200
        assert user.get('/api/auth/me').json()['mustChangePassword']
        assert user.get('/api/cases').status_code==403
        assert user.post('/api/auth/change-password',headers=auth,json={
          'current_password':'ForcedTemporaryCredential2026!',
          'new_password':'FinishedRotationCredential2026!'}).status_code==200
        assert user.post('/api/auth/login',json={'username':'forceduser','password':'FinishedRotationCredential2026!'}).status_code==200
        assert user.get('/api/cases').status_code==200
        deactivated=client.patch(f'/api/users/{uid}/status',headers=auth,json={
          'active':False,'administrator_password':'AnIntentionallyLongTestPassword123'})
        assert deactivated.status_code==200,deactivated.text
        assert user.get('/api/auth/me').status_code==401
        assert user.post('/api/auth/login',json={'username':'forceduser','password':'FinishedRotationCredential2026!'}).status_code==401

def test_mfa_sso_is_not_falsely_claimed(client,auth):
    cap=client.get('/api/auth/security-capabilities')
    assert cap.status_code==200
    assert cap.json()['phishingResistantMfa'] is False
    assert cap.json()['organizationSso'] is False
