"""Fail-closed safeguards for externally transmitted research and allegations.

Signals indicate *review requirements*, not that an allegation is true.
Never automatically infer sensitive traits or private location/contact details.
"""
import re
from fastapi import HTTPException

PRIVATE_SEARCH = [
    (re.compile(r'\b(?:home|residential|private)\s+(?:street\s+)?address\b',re.I),'residential_address'),
    (re.compile(r'\b(?:live|real[- ]?time|current|precise)\s+(?:gps\s+)?(?:location|coordinates|whereabouts)\b',re.I),'realtime_location'),
    (re.compile(r'\b(?:track|stalk|follow|surveil)\s+(?:this\s+|the\s+)?(?:person|individual|student|woman|man|employee)\b',re.I),'person_tracking'),
    (re.compile(r'\b(?:private|personal|unlisted)\s+(?:mobile|phone|email|contact|number)\b',re.I),'private_contact'),
    (re.compile(r'\b(?:aadhaar|aadhar|social security number|passport number|bank account number|credit card number)\b',re.I),'restricted_identifier'),
    (re.compile(r'\b(?:infer|predict|guess|determine)\s+(?:their|his|her|the)\s+(?:religion|caste|sexual orientation|medical condition|political affiliation)\b',re.I),'sensitive_inference')
]
ALLEGATIONS=re.compile(
 r'\b(?:fraud|bribery|corruption|terroris(?:m|t)|extremis(?:m|t)|rape|'
 r'murder|sexual assault|money laundering|trafficking|criminal|'
 r'child abuse|harassment|sexual misconduct|scam(?:mer)?|convicted)\b',re.I)


def classify_remote_query(query,subject_type='person'):
    if subject_type!='person':
        return {'allowed':True,'blockedCategories':[],'identityVerified':False}
    signals=[key for pattern,key in PRIVATE_SEARCH if pattern.search(str(query or ''))]
    return {'allowed':not bool(signals),'blockedCategories':list(dict.fromkeys(signals)),
            'identityVerified':False,'requiresSpecificCasePurpose':True,
            'externalDataRecipients':'Configured public-source providers and opted-in AI services'}


def require_safe_remote_query(query,subject_type='person'):
    result=classify_remote_query(query,subject_type)
    if not result['allowed']:
        raise HTTPException(422,'Private-person query is outside the permitted public research scope: '+
                            ', '.join(result['blockedCategories'])+'.')
    return result


def guard_high_risk_claim(answer,question,subject_type):
    """Never publish an unadjudicated person allegation as a factual finding."""
    if subject_type!='person' or not ALLEGATIONS.search(str(answer or '')):
        return {'action':'no_high_risk_claim_detected','answer':answer,
                'automaticallyApproved':False}
    return {'action':'withhold_unreviewed_serious_allegation',
        'answer':('The generated response mentioned a serious allegation. '
                  'It is withheld because the system has not independently verified '
                  'the identity, authoritative original records, contradictory evidence '
                  'and a human review decision. This does not establish wrongdoing.'),
        'automaticallyApproved':False,
        'requires':['authoritative original source','identity disambiguation',
                    'adverse and exculpatory source review','authorized human approval']}
