"""Least-information sensitive evidence inventory; never return excerpts or credentials."""
from __future__ import annotations
from fastapi import APIRouter,Depends
from . import db,main as core
router=APIRouter()

@router.get('/api/cases/{case_id}/data-protection-review')
def data_protection_review(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        def count(sql):
            return conn.execute(sql,(case_id,)).fetchone()['n']
        findings={
         'sourceTextCaptures':count('SELECT count(*) n FROM source_captures WHERE case_id=?'),
         'retainedOriginalArtifacts':count('SELECT count(*) n FROM source_document_archives WHERE case_id=?'),
         'humanTranslationRecords':count('SELECT count(*) n FROM translation_capture_reviews WHERE case_id=?'),
         'storedOriginalExcerpts':count('SELECT count(*) n FROM research_excerpt_samples WHERE case_id=?'),
         'savedAssistantMessages':count('SELECT count(*) n FROM research_messages WHERE case_id=? AND role=\'assistant\''),
         'unreviewedSources':count("SELECT count(*) n FROM evidence WHERE case_id=? AND status='candidate'")}
        policy=conn.execute('SELECT legal_hold,review_after FROM case_preservation_policy WHERE case_id=?',(case_id,)).fetchone()
    return {'caseId':case_id,'itemCountsOnly':findings,
       'preservationHold':bool(policy and policy['legal_hold']),
       'policyReviewDate':policy['review_after'] if policy else None,
       'payloadsReturned':False,'databaseEncryptionVerified':False,
       'applicationEnvelopeEncryptionEnabled':False,'kmsKeyRotationVerified':False,
       'backupDeletionVerified':False,'privacyComplianceCertified':False,
       'notice':'Captured source text, case notes and binary archives may contain third-party personal information. Counts only; verify storage, KMS, backups and legal basis before deployment.'}
