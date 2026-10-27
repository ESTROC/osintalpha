"""Prevent cross-candidate merging when drafting person findings."""
from collections import defaultdict

def partition_candidate_records(records, profiles, links):
    by_id={str(r.get('id')):r for r in records}
    groups={str(p['id']):{'candidateId':str(p['id']),
        'label':str(p['display_name'])[:180],
        'reviewClassification':str(p.get('classification') or 'unresolved'),
        'identityVerified':False,'evidence':[]} for p in profiles}
    members=defaultdict(set)
    for link in links:
        p,e=str(link.get('profile_id')),str(link.get('evidence_id'))
        if p in groups and e in by_id:members[e].add(p)
    ambiguous=[];unassigned=[]
    for eid,record in by_id.items():
        assigned=members.get(eid,set())
        if len(assigned)==1:groups[next(iter(assigned))]['evidence'].append(record)
        elif len(assigned)>1:ambiguous.append({
            'record':record,'candidateIds':sorted(assigned),
            'reason':'Multiple hypotheses; cannot merge.'})
        else:unassigned.append(record)
    return {'candidates':[g for g in groups.values() if g['evidence']],
        'unassignedLeads':unassigned,'crossLinkedAmbiguousLeads':ambiguous,
        'verifiedIdentity':False,'crossCandidateSynthesisAllowed':False,
        'warning':'Candidate evidence is hypothetical; never merge different namesakes.'}

def load_candidate_partitions(conn,case_id,records):
    profiles=[dict(r) for r in conn.execute(
        'SELECT id,display_name,classification FROM candidate_profiles WHERE case_id=?',
        (case_id,))]
    links=[dict(r) for r in conn.execute(
        'SELECT ce.profile_id,ce.evidence_id FROM candidate_evidence ce '
        'JOIN candidate_profiles p ON p.id=ce.profile_id '
        'JOIN evidence e ON e.id=ce.evidence_id '
        'WHERE p.case_id=? AND e.case_id=?',(case_id,case_id))]
    return partition_candidate_records(records,profiles,links)
