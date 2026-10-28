"""P1 087: client-reported provider failures persist and remain explicitly unverified."""
def test_client_stage_outcome_saved_for_case(client,auth,case):
    req={'stage':'brave_context','outcome':'fallback',
         'reason':'provider_error','original_question':'Public synthetic source analysis'}
    r=client.post(f'/api/cases/{case}/client-stage-events',headers=auth,json=req)
    assert r.status_code==201,r.text
    assert r.json()['source']=='client_reported_not_provider_verified'
    saved=client.get(f'/api/cases/{case}/client-stage-events')
    assert saved.status_code==200,saved.text
    assert saved.json()['items'][0]['status']=='fallback'
    assert saved.json()['providerConfirmed'] is False
    d=client.get(f'/api/cases/{case}/dossier').json()
    assert d['identityVerified'] is False
    assert d['providerFailures'][0]['status']=='fallback'

def test_cannot_write_stage_data_to_noncase(client,auth):
    req={'stage':'groq_analysis','outcome':'error',
         'reason':'other','original_question':'Synthetic public research'}
    assert client.post('/api/cases/noncase/client-stage-events',headers=auth,json=req).status_code==404
    req['stage']='unsupported_custom_provider'
    assert client.post('/api/cases/noncase/client-stage-events',headers=auth,json=req).status_code==422
