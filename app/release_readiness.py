"""Administrator-only pilot acceptance and security gate inventory.

A successful test or provisioned database is not evidence of independent
operational, legal, or regulated-agency production acceptance.
"""
from __future__ import annotations
import os
from fastapi import APIRouter,Depends
from fastapi.responses import JSONResponse
from . import db,main as core
from .release import VERSION
router=APIRouter()

def gate(code,title,state,next_action,observed=None):
    return {'id':code,'title':title,'state':state,'observation':observed,
            'nextAction':next_action,'independentlyCertified':False}

def readiness_snapshot():
    with db.connect() as conn:
        conn.execute('SELECT 1').fetchone()
        rights=[dict(x) for x in conn.execute(
          'SELECT rights_status,count(*) n FROM provider_terms_reviews GROUP BY rights_status')]
    reviews={x['rights_status']:x['n'] for x in rights}
    cookie=os.getenv('OSINTALPHA_SECURE_COOKIE')=='1'
    postgres=db.is_postgres()
    return {'releaseVersion':VERSION,
      'stage':'research-pilot-not-regulated-production',
      'productionApproved':False,
      'all152IndependentlyAccepted':False,
      'checksProveExternalCompliance':False,
      'configuration':{'postgresConfigured':postgres,
          'secureCookieFlagConfigured':cookie,
          'providerPolicyReviewsCount':reviews,
          'databaseBackupVerified':False,
          'liveSourceAccuracyVerified':False},
      'gates':[
        gate('storage','Long-lived database and verified restore',
             'configured_not_verified' if postgres else 'blocked',
             'Choose durable storage with owner approval; independently test encrypted backup and recovery.'),
        gate('session_transport','HTTPS/session and cookie protection',
             'configured_not_verified' if cookie else 'blocked',
             'Verify HTTPS, proxy, CSRF and secure cookies in production browsers.'),
        gate('phishing_resistant_mfa','Phishing-resistant MFA and organization SSO','blocked',
             'Integrate and audit a real WebAuthn or organization identity provider.'),
        gate('publisher_rights','Source API rights and lawful uses','unverified',
             'Obtain publisher permissions and independent legal review. Admin marks do not grant a license.'),
        gate('sensitive_data_protection','Encryption, retention and privacy','unverified',
             'Verify KMS, restricted exports, incident controls and authorized retention/erasure.'),
        gate('database_recovery','Backup and disaster recovery','unverified',
             'Complete a witnessed restore and recurring recovery drill on a supported database plan.'),
        gate('independent_identity_quality','Real-world namesake/citation accuracy','unverified',
             'Measure false matches and claim-to-original correctness on authorized independent cases.'),
        gate('analyst_acceptance','Independent analyst usability and accessibility','unverified',
             'Conduct consented analyst tasks and manual screen-reader/WCAG verification.'),
        gate('optional_external_engines','Third-party engine site permissions','blocked',
             'Authorize site allowlists, passive isolation and false-positive benchmarks before enabling.'),
        gate('live_monitoring','Monitoring, incidents and upstream service SLAs','unverified',
             'Set up independent uptime probes, on-call alerts and dated provider outage evidence.')
      ],
      'notice':'This is a noncertifying acceptance checklist. It never returns case evidence, credentials, provider keys or stored personal identifiers.'
    }

@router.get('/api/admin/release-readiness')
def release_readiness(actor=Depends(core.actor_from_cookie)):
    core.admin_only(actor)
    return JSONResponse(readiness_snapshot(),headers={'Cache-Control':'no-store'})
