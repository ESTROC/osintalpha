"""P1-084 licensed source thumbnail gating; no unsourced person photo inference."""
import json
from app.case_dossier import licensed_preview

def test_084_rejects_unlicensed_google_image_metadata():
    x={'raw_json':json.dumps({'thumbnail_url':'https://random.example.org/person.jpg',
        'thumbnail_license':'CC-BY-4.0','thumbnail_credit':'Unknown uploader',
        'thumbnail_license_url':'https://creativecommons.org/licenses/by/4.0/'})}
    assert licensed_preview(x) is None

def test_084_allow_explicit_licensed_commons_media_without_identity_claim():
    x={'raw_json':json.dumps({
        'thumbnail_url':'https://upload.wikimedia.org/wikipedia/commons/a/a1/public-event.jpg',
        'thumbnail_license':'CC-BY-4.0',
        'thumbnail_credit':'Published photographer (metadata)',
        'thumbnail_license_url':'https://creativecommons.org/licenses/by/4.0/'})}
    m=licensed_preview(x)
    assert m['sourceMediaNotPersonIdentification']
    assert not m['subjectIdentityVerified']
    assert m['license']=='CC-BY-4.0'

def test_084_license_not_proven_if_credit_missing():
    x={'raw_json':json.dumps({'thumbnail_url':'https://upload.wikimedia.org/wikipedia/commons/a/a1/photo.jpg',
      'thumbnail_license':'CC0-1.0',
      'thumbnail_license_url':'https://creativecommons.org/publicdomain/zero/1.0/'})}
    assert licensed_preview(x) is None
