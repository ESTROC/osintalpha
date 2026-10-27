"""P0 014: instrumentation must never fabricate a live pass."""
from app.provider_validation import summarize_provider_evidence


def test_014_source_ledger_cannot_certify_real_provider():
    result=summarize_provider_evidence(
        [{'provider':'brave_web','status':'ok','query_text':'example'},
         {'provider':'groq','status':'error','query_text':'example'}],
        [{'provider':'brave_llm_context','source_url':'https://example.org/page'}])
    assert result['liveProviderAcceptancePassed'] is False
    assert all(not p['independentCitationAccuracyVerified']
               for p in result['providers'])


def test_014_case_scope_and_empty_telemetry(client,auth,case):
    r=client.get(f'/api/cases/{case}/provider-validation')
    assert r.status_code==200
    assert r.json()['providers']==[]
    assert not r.json()['independentGroundTruthReviewed']
    assert client.get('/api/cases/nonexistent/provider-validation').status_code==404
