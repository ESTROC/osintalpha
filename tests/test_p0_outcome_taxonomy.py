"""P0 026: not searched, not found, disputed, rejected and mismatched are distinct."""
from app.source_completeness import summarize

def test_026_no_hits_are_not_mismatch():
    r=summarize([{'provider':'github','state':'empty','ran_at':'2026-10-28'}])
    assert r['distinctions']['providerNoHits']==1
    assert r['distinctions']['wrongIdentityIndependentlyProven']==0
    assert not r['wrongIdentityVerified']

def test_026_rejected_and_disputed_are_distinct():
    r=summarize([],[{'status':'rejected'},{'status':'disputed'},{'status':'candidate'}])
    assert r['distinctions']['analystRejected']==1
    assert r['distinctions']['analystDisputed']==1
    assert r['distinctions']['unreviewedCandidate']==1
    assert r['distinctions']['wrongIdentityIndependentlyProven']==0

def test_026_failed_and_not_searched_are_separate():
    r=summarize([{'provider':'brave_web','state':'error','ran_at':'2026-10-28'}],
                expected=['brave_web','openalex'])
    assert r['distinctions']['providerFailed']==1
    assert r['distinctions']['notSearched']==1
