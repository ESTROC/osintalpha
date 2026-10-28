"""P3-152 status distinguishes live API/DB response from continuous uptime."""
def test_public_status_and_operator_notice(client,auth,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','SENSITIVE_FAKE_PROVIDER_TEST_KEY')
    info=client.get('/api/public/status')
    assert info.status_code==200,info.text
    assert info.json()['appDatabaseResponding']
    assert info.json()['providerUptimeVerified'] is False
    assert info.json()['continuousMonitoringEnabled'] is False
    assert 'SENSITIVE_FAKE_PROVIDER_TEST_KEY' not in info.text
    page=client.get('/status')
    assert page.status_code==200
    assert 'No operator incident notice is recorded' in page.text
    publish=client.post('/api/admin/service-notices',headers=auth,json={
        'state':'degraded','message':'Synthetic provider degradation; official provider credentials are not logged.'})
    assert publish.status_code==201,publish.text
    after=client.get('/api/public/status')
    assert after.status_code==200
    assert after.json()['currentPublishedNotice']=='degraded'
    assert after.json()['publishedNotices'][0]['status']=='degraded'
    assert 'Synthetic provider degradation' in client.get('/status').text
