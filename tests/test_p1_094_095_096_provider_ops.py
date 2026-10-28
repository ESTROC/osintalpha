"""P1-094/095/096 durable daily limits, bounded circuit cooldown and measured-call disclosure."""
from fastapi import HTTPException
from app import db
from app.provider_ops import reserve,cooling,record,limit

def test_daily_external_call_cap_is_case_scoped(client,auth,case,monkeypatch):
    monkeypatch.setenv('OSINTALPHA_CASE_DAILY_BRAVE_WEB_LIMIT','2')
    with db.connect() as c:
        owner=c.execute('SELECT created_by FROM cases WHERE id=?',(case,)).fetchone()['created_by']
    reserve(case,owner,'brave_web')
    reserve(case,owner,'brave_web')
    try:reserve(case,owner,'brave_web')
    except HTTPException as e:assert e.status_code==429
    else:assert False,'budget cap did not trigger'
    result=client.get(f'/api/cases/{case}/research-budget')
    assert result.status_code==200
    entry=next(x for x in result.json()['dailyCallReservations'] if x['provider']=='brave_web')
    assert entry['used']==2 and entry['remaining']==0
    assert result.json()['estimatedCurrencyCost'] is None

def test_cooldown_requires_three_recent_errors(client):
    assert not cooling('github')
    for n in range(3):record('github','throttled',80,429)
    assert cooling('github')
    record('github','ok',12,200)
    assert not cooling('github')

def test_authorized_health_has_no_fake_uptime(client,auth):
    response=client.get('/api/research/source-health')
    assert response.status_code==200,response.text
    assert not response.json()['continuousSyntheticMonitoring']
    assert response.json()['serviceLevelTarget'] is None
