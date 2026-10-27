"""P0 018: same-name sources are separate unverified hypotheses."""
from app.candidate_partition import partition_candidate_records

def test_018_two_candidates_not_conflated():
    records=[{'id':'a','label':'A'},{'id':'b','label':'B'}]
    profiles=[{'id':'p1','display_name':'Same Name'},
              {'id':'p2','display_name':'Same Name'}]
    links=[{'profile_id':'p1','evidence_id':'a'},
           {'profile_id':'p2','evidence_id':'b'}]
    data=partition_candidate_records(records,profiles,links)
    assert len(data['candidates'])==2
    assert [g['evidence'] for g in data['candidates']]==[[records[0]],[records[1]]]
    assert data['crossCandidateSynthesisAllowed'] is False

def test_018_multi_link_is_ambiguous():
    r=[{'id':'s'}]
    p=[{'id':'p1','display_name':'Alex'},{'id':'p2','display_name':'Alex'}]
    links=[{'profile_id':'p1','evidence_id':'s'},{'profile_id':'p2','evidence_id':'s'}]
    data=partition_candidate_records(r,p,links)
    assert len(data['crossLinkedAmbiguousLeads'])==1
    assert not data['candidates'] and not data['verifiedIdentity']

def test_018_unlinked_hits_stay_unassigned():
    data=partition_candidate_records([{'id':'a'}],
        [{'id':'p','display_name':'Alex'}],
        [{'profile_id':'p','evidence_id':'outside_case'}])
    assert data['unassignedLeads']==[{'id':'a'}]
