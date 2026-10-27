"""V7.8: broad public inquiry and opt-in, attributed Brave-to-Groq context.

Mocks do not demonstrate live provider or factual accuracy.
"""
import asyncio
import json
from types import SimpleNamespace

from app import brave_context, main, v5


def test_research_lenses_support_non_academic_subjects():
    case = {'subject_type': 'person', 'query': 'Sample Person'}
    context = {'city': 'Delhi', 'organization': '', 'profession': '', 'public_handle': ''}
    def queries(lens):
        return v5.make_queries(case, context, SimpleNamespace(query=None, depth=4, lens=lens))
    general = queries('general')
    assert len(general) == 4 and any('community OR business OR event' in x for x in general)
    assert not any('site:linkedin.com/in/' in x for x in general)
    assert any('trade OR service' in x for x in queries('trade'))
    assert any('school OR college' in x for x in queries('education'))
    assert any('site:linkedin.com/in/' in x for x in queries('professional'))


def test_brave_excerpts_only_allow_public_https_with_explicit_sources():
    data = {'grounding': {'generic': [
        {'url': 'https://example.org/public-page', 'title': 'Public community record',
         'snippets': ['An independently unverified community entry.']},
        {'url': 'https://127.0.0.1/admin', 'snippets': ['private network should not be included']},
        {'url': 'http://example.org/insecure', 'snippets': ['not secure']},
        {'url': 'https://example.org/public-page', 'snippets': ['duplicate']},
    ]}, 'sources': {'https://example.org/public-page': {
        'age': ['date', '2026-10-26', '1 day ago', '2026-10-26T12:00:00Z']}}}
    entries = brave_context.parse_context(data)
    assert len(entries) == 1 and entries[0]['sourceDate'] == '2026-10-26T12:00:00Z'
    assert entries[0]['status'] == 'unverified_extracted_search_context'


def test_brave_source_links_cannot_be_hallucinated():
    answer = ('[Evidence](https://example.org/known) '
              '[Invented](https://example.org/not-seen)')
    cleaned = brave_context.clean_answer_links(answer,
             [{'url': 'https://example.org/known'}], [])
    assert '[Evidence](https://example.org/known)' in cleaned
    assert '[Invented](' not in cleaned
    assert 'unverified link omitted' in cleaned


def test_restrict_live_person_tracking_and_home_addresses():
    case = {'query': 'Sample Person'}
    for q in ('Track this person now', 'Find the home address',
              'What is the live location of Sample Person?'):
        try:
            brave_context.composed_query(case, q, {})
        except Exception as exc:
            assert getattr(exc, 'status_code', None) == 422
        else:
            raise AssertionError('Private-person tracking request was not rejected')
    assert 'Sample Person' in brave_context.composed_query(
        case, 'Is a public business registration documented?', {'city': 'Delhi'})


def test_brave_live_context_query_has_fixed_budget(monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY', 'synthetic-test-key')
    calls = []
    class Response:
        def raise_for_status(self): return None
        def json(self): return {
            'grounding': {'generic': [
                {'url': 'https://community.example.org/record', 'title': 'Source',
                 'snippets': ['Public entry about an activity']}]},
            'sources': {}}
    class Client:
        async def post(self, url, headers, json):
            calls.append((url, headers, json))
            return Response()
    out = asyncio.run(brave_context.retrieve(
        {'query': 'Sample Person'}, 'What public work is documented?', {},
        client=Client()))
    assert out['searchedNow'] and len(out['sources']) == 1
    assert calls[0][0] == 'https://api.search.brave.com/res/v1/llm/context'
    assert calls[0][2]['maximum_number_of_urls'] == 8
    assert calls[0][2]['enable_local'] is False
    assert calls[0][1]['X-Subscription-Token'] == 'synthetic-test-key'


def test_brave_context_is_separate_opt_in_and_requires_consent(client, auth, case, monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic-groq-key')
    body = {'provider': 'groq', 'question': 'Public source question', 'brave_context': True}
    assert client.post('/api/cases/' + case + '/chat', headers=auth, json=body).status_code == 403
    assert client.post('/api/cases/' + case + '/chat', headers=auth, json={
        **body, 'web_search': True}).status_code == 422
    assert client.post('/api/cases/' + case + '/chat', headers=auth, json={
        **body, 'provider': 'local'}).status_code == 422


def test_groq_gets_recent_brave_sources_and_exposes_attributed_urls(client, auth, case, monkeypatch):
    from app import brave_context as bc
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic-groq-key')
    client.put('/api/cases/' + case + '/ai-consent',
               headers=auth, json={'enabled': True})
    calls = []
    async def stub_retrieve(case, question, clues, **kwargs):
        calls.append(('brave', question))
        return {'searchedNow': True, 'sources': [{
            'url': 'https://public.example.org/community-page',
            'title': 'Public activity', 'snippet': 'Unverified public event notice',
            'sourceDate': '', 'status': 'unverified_extracted_search_context'
        }], 'provider': 'Brave LLM Context'}
    monkeypatch.setattr(bc, 'retrieve', stub_retrieve)
    class Response:
        def raise_for_status(self): return None
        def json(self):
            return {'choices': [{'message': {'content': json.dumps({
                'answer': 'Source mentions an event [Source](https://public.example.org/community-page)',
                'evidence_ids': [], 'follow_up': '', 'needs_disambiguation': True})}}]}
    class ModelClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, json, headers):
            assert url == 'https://api.groq.com/openai/v1/chat/completions'
            assert 'freshUnverifiedBraveContext' in json['messages'][1]['content']
            assert json['response_format']['json_schema']['strict']
            assert 'tools' not in json
            return Response()
    monkeypatch.setattr(main.httpx, 'AsyncClient', ModelClient)
    r = client.post('/api/cases/' + case + '/chat', headers=auth, json={
        'provider': 'groq', 'question': 'Which public community event is documented?',
        'brave_context': True})
    assert r.status_code == 200, r.text
    result = r.json()
    assert result['braveContextUsed'] is True and result['freshSourcesCount'] == 1
    assert result['webLeads'][0]['url'] == 'https://public.example.org/community-page'
    assert '[Source](' in result['answer']
    assert len(calls) == 1
