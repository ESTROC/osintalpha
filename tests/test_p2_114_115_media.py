"""P2 114-115: no fake live camera frame or unlicensed satellite layer."""
from app.media_governance import camera_publisher_status,known_publisher_image

def test_camera_timestamp_unknown_and_untrusted_image_blocked():
    cases=[{'provider':'Caltrans','feedUrl':'http://evil.example/cam.jpg'},
           {'provider':'Caltrans','feedUrl':'https://cwwp2.dot.ca.gov/vm/example.jpg'}]
    out=camera_publisher_status(cases,'caltrans')
    assert out[0]['feedUrl'] is None and out[0]['frameCapturedAt'] is None
    assert out[1]['frameAgeKnown'] is False
    assert out[1]['personIdentificationVerified'] is False
    assert not out[1]['publisherImageUseRightsVerified']

def test_satellite_unauthorized_reference_fails(client,auth,case):
    r=client.get(f'/api/cases/{case}/licensed-satellite-references')
    assert r.status_code==200,r.text
    assert not r.json()['hasRasterLayer']
    payload={'evidence_id':'not-present','provider':'nasa_gibs',
      'official_catalog_url':'https://gibs.earthdata.nasa.gov/',
      'permission_url':'https://earthdata.nasa.gov/',
      'acquisition_date':'2025-10-01','ground_resolution_m':250,
      'crs':'EPSG:4326','bounding_box':[-120,30,-119,31],
      'review_note':'Synthetic metadata, no license rights or real raster obtained.',
      'rights_confirmed':False}
    assert client.post(f'/api/cases/{case}/licensed-satellite-references',
                       headers=auth,json=payload).status_code==422
