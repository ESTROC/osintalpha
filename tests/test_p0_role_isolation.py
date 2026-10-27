"""P0-025: separate restricted user, cross-case denial and admin isolation.

These are synthetic permissions tests, NOT a real Shalini/agency account.
"""
def test_025_restricted_analyst_cannot_read_other_users_case_or_exports(client,auth,case):
    created=client.post('/api/users',headers=auth,json={
        'username':'restricted_025','password':'RestrictedTestPasswordValid123',
        'role':'analyst'})
    assert created.status_code==201
    assert client.post('/api/auth/logout',headers=auth).status_code==200
    login=client.post('/api/auth/login',json={
        'username':'restricted_025','password':'RestrictedTestPasswordValid123'})
    assert login.status_code==200
    protected=[
        f'/api/cases/{case}', f'/api/cases/{case}/report.json',
        f'/api/cases/{case}/report.html',f'/api/cases/{case}/report.pdf',
        f'/api/cases/{case}/source-completeness',
        f'/api/cases/{case}/provider-validation',
        f'/api/cases/{case}/authorization',
        f'/api/cases/{case}/claim-passages',
        f'/api/cases/{case}/jobs',
        f'/api/cases/{case}/search-plan']
    for path in protected:
        assert client.get(path).status_code==404,path
    assert client.post(f'/api/cases/{case}/chat',headers=auth,
        json={'question':'Show sources','provider':'local'}).status_code==404
    assert client.post(f'/api/cases/{case}/collect',headers=auth,
        json={'providers':['github']}).status_code==404
    assert client.post(f'/api/cases/{case}/authorization',headers=auth,
        json={'specific_scope':'Case scope unrelated to this analyst case',
              'authorization_category':'internal_public_research',
              'approval_reference':'OUT-OF-SCOPE-025',
              'retention_days':30,'approve':True}).status_code==403
    assert client.get('/api/users').status_code==403


def test_025_invalid_user_credentials_do_not_authenticate(client,auth):
    r=client.post('/api/auth/login',json={
        'username':'restricted_unknown_025','password':'UnrecognizedTestPassword'})
    assert r.status_code in (401,403,429)
