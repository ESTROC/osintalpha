"""P0 019/020: fail closed on given-name web search; preserve the full objective."""
import pytest
from app import v5
from app import db


def test_019_given_name_requires_public_discriminator(client,auth,case,monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','synthetic-no-network')
    response=client.post(f'/api/cases/{case}/web-discovery',headers=auth,
          json={'consent':True,'query':'Alex','depth':1})
    assert response.status_code==422
    assert 'single given name' in response.json()['detail'].lower()


def test_020_full_original_question_not_replaced_by_case_name():
    body=v5.WebSearchInput(consent=True,depth=1)
    case={'query':'Maya Singh','subject_type':'person'}
    assert v5.make_queries(case,{},body,
        'What public engineering activities were reported for Maya Singh in Delhi?')[0].startswith(
        'What public engineering activities')


def test_020_explicit_override_remains_explicit():
    body=v5.WebSearchInput(consent=True,query='Maya Singh awarded university prize',depth=1)
    case={'query':'Maya Singh','subject_type':'person'}
    assert v5.make_queries(case,{},body,'What did Maya Singh do?')[0] == body.query


def test_020_original_question_is_saved_for_replay(client,auth):
    response=client.post('/api/search/start',headers=auth,json={
        'question':'What public projects did Maya Singh build at university?',
        'purpose':'Research documented public engineering activities',
        'authority_confirmed':True})
    assert response.status_code==201
    ident=response.json()['id']
    with db.connect() as conn:
        original=conn.execute('SELECT original_question FROM case_search_plans WHERE case_id=?',
                              (ident,)).fetchone()['original_question']
    assert original=='What public projects did Maya Singh build at university?'
