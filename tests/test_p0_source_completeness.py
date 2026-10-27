"""P0-011 and P0-026: source states and identity outcomes remain distinct."""
from app.source_completeness import summarize


def test_011_empty_is_not_proof_of_absence():
    data = summarize([{'provider':'github','state':'empty','ran_at':'2026-10-28T00:00:00Z',
                       'result_count':0,'message':'0 hits'}], expected=['github'])
    assert data['outcome'] == 'no_hits_in_attempted_sources'
    assert data['canConcludeSubjectOrClaimAbsent'] is False


def test_011_failed_provider_is_not_empty():
    data = summarize([{'provider':'brave_web','state':'error','ran_at':'2026-10-28',
                       'message':'rate limited'}], expected=['brave_web','crossref'])
    assert data['providerCounts'] == {'error': 1, 'not_searched': 1}
    assert data['outcome'] == 'incomplete_provider_failures'


def test_011_latest_failure_is_not_hidden_by_older_success():
    data = summarize([
        {'provider':'github','state':'ok','ran_at':'2026-10-27','result_count':5},
        {'provider':'github','state':'error','ran_at':'2026-10-28','result_count':0},
    ])
    assert data['providerStates'][0]['state'] == 'error'


def test_026_rejected_lead_is_not_proof_of_wrong_person():
    data = summarize([], [{'status':'rejected'}])
    assert data['analystRejectedCount'] == 1
    assert data['candidateCount'] == 0
    assert data['identityVerified'] is False
    assert data['canConcludeSubjectOrClaimAbsent'] is False


def test_011_endpoint_is_case_scoped(client, auth, case):
    with __import__('app.db', fromlist=['connect']).connect() as conn:
        conn.execute('INSERT INTO collection_runs VALUES (?,?,?,?,?,?,?)',
                     ('test-run', case, 'github', 'error', 0, 'synthetic failure',
                      '2026-10-28T00:00:00Z'))
    response = client.get(f'/api/cases/{case}/source-completeness')
    assert response.status_code == 200
    assert response.json()['outcome'] == 'incomplete_provider_failures'
    assert response.json()['identityVerified'] is False
    assert client.get('/api/cases/not-a-case/source-completeness').status_code == 404
