"""P2-137 initial case bundle equals separate existing authorized API contracts."""
def test_initial_view_case_scope_and_required_sections(client,auth,case):
    response=client.get(f'/api/cases/{case}/initial-view')
    assert response.status_code==200,response.text
    data=response.json()
    for name in ('triage','conversations','researchPlan','runs','intelligence',
       'webProviders','candidates','queryExplain','readiness','searchProgress',
       'dossier','budget','draft','refinements'):
        assert name in data,name
    assert data['initialRoundTripCount']==1
    assert data['dossier']['caseId']==case
    assert not data['sourceTruthVerified']
    assert client.get('/api/cases/unrelated-case/initial-view').status_code==404

def test_frontend_uses_single_auth_initial_bundle():
    from pathlib import Path
    js=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    segment=js[js.index('async function loadResearchState(){'):js.index('async function loadAdvancedCaseState(tab)')]
    assert "initial-view?depth=" in segment
    assert "if(!all?.initialRoundTripCount)" in segment
    assert "s.dossier=all.dossier" in segment
