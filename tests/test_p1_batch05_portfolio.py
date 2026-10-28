"""P1 072/073: indexed article/photo is not verified person identity."""
from app.portfolio import source_account_type,safe_github_avatar

def test_073_repositories_and_blogs_are_not_account_profiles():
    assert source_account_type('github','https://github.com/org/repo',{})=='document_or_mention'
    assert source_account_type('github','https://github.com/public-user',{})=='public_account_candidate'
    assert source_account_type('brave_web','https://www.linkedin.com/in/candidate',{})=='document_or_mention'
    assert source_account_type('analyst','https://news.example.org/article',{})=='document_or_mention'

def test_072_safe_avatar_only_source_cdn():
    assert safe_github_avatar('https://avatars.githubusercontent.com/u/12345')
    assert not safe_github_avatar('https://evil.example.com/some-face.png')

def test_073_case_portfolio_separates_bare_mentions(client,auth,case):
    response=client.post(f'/api/cases/{case}/evidence',headers=auth,json={
       'label':'Community article','summary':'Unverified public article about a name',
       'source_url':'https://example.org/article'})
    assert response.status_code==200
    result=client.get(f'/api/cases/{case}/public-portfolio')
    assert result.status_code==200,result.text
    data=result.json()
    assert not data['accountCandidates']
    assert data['documentsAndMentions']
    lead=data['documentsAndMentions'][0]
    assert not lead['isProfileAccount']
    assert lead['photoAttribution']=='source_account_only_not_subject_identification'
    assert not lead['faceIdentityVerified']
