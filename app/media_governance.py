"""Trusted public camera frame metadata and manually licensed satellite references."""
from __future__ import annotations
import json,re
from datetime import date
from urllib.parse import urlsplit
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from . import db,main as core
router=APIRouter()

def known_publisher_image(url,kind):
    if not isinstance(url,str) or len(url)>600:return None
    try:
        p=urlsplit(url)
        if p.scheme!='https' or p.username or p.password or p.port not in (None,443):
            return None
        host=(p.hostname or '').lower()
        if kind=='tfl':
            if host!='s3-eu-west-1.amazonaws.com' or not p.path.startswith('/jamcams.tfl.gov.uk/'):
                return None
        elif kind=='caltrans':
            if host not in ('cwwp2.dot.ca.gov','cwwp.dot.ca.gov','dot.ca.gov'):
                return None
        else:return None
        if p.fragment:return None
        return url
    except ValueError:return None

def camera_publisher_status(items,provider):
    """No invented frame timestamp; publisher-listed URL alone means freshness unknown."""
    normalized=[]
    for row in items:
        x=dict(row)
        url=known_publisher_image(x.get('feedUrl'),provider)
        x['feedUrl']=url
        x['frameCapturedAt']=None
        x['frameAgeKnown']=False
        x['frameStatus']='publisher_listed_timestamp_unknown' if url else 'no_permitted_current_still'
        x['personIdentificationVerified']=False
        x['publisherImageUseRightsVerified']=False
        x['publisherAttribution']=x.get('attribution') or x.get('provider')
        normalized.append(x)
    return normalized

class SatelliteReference(BaseModel):
    evidence_id:str
    provider:Literal['nasa_gibs','copernicus_dataspace']
    official_catalog_url:str=Field(min_length=20,max_length=500)
    permission_url:str=Field(min_length=20,max_length=500)
    acquisition_date:date
    ground_resolution_m:float=Field(gt=0,le=100000)
    crs:str=Field(pattern=r'^EPSG:[0-9]{4,6}$')
    bounding_box:tuple[float,float,float,float]
    review_note:str=Field(min_length=40,max_length=600)
    rights_confirmed:bool=False

def allowed_provider_link(url,provider):
    try:
        p=urlsplit(url)
        host=(p.hostname or '').lower()
        if p.scheme!='https' or p.username or p.password or p.port not in (None,443):
            return False
        if provider=='nasa_gibs':
            return host.endswith('.earthdata.nasa.gov') or host=='earthdata.nasa.gov'
        return host.endswith('.dataspace.copernicus.eu') or host=='dataspace.copernicus.eu'
    except ValueError:return False

@router.post('/api/cases/{case_id}/licensed-satellite-references',status_code=201)
def record_reference(case_id:str,body:SatelliteReference,actor=Depends(core.protect)):
    core.admin_only(actor)
    if not body.rights_confirmed:raise HTTPException(422,'Public imagery rights confirmation is required.')
    if not (allowed_provider_link(body.official_catalog_url,body.provider) and
            allowed_provider_link(body.permission_url,body.provider)):
        raise HTTPException(422,'Catalog and permissions must link to the nominated official publisher.')
    west,south,east,north=body.bounding_box
    if not all((-180<=west<east<=180,-90<=south<north<=90)):
        raise HTTPException(422,'Invalid acquisition bounding box.')
    with db.connect() as conn:
        case=core.case_or_404(conn,case_id,actor)
        if case['subject_type']=='person':
            raise HTTPException(422,'Satellite geospatial references cannot be associated with individual-person investigations.')
        src=conn.execute('SELECT id,status FROM evidence WHERE id=? AND case_id=?',
             (body.evidence_id,case_id)).fetchone()
        if not src or src['status']!='corroborated':
            raise HTTPException(422,'A reviewed public publisher source is required.')
        ident=core.uid()
        conn.execute('INSERT INTO licensed_satellite_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
         (ident,case_id,body.evidence_id,body.provider,body.official_catalog_url,
          body.permission_url,body.acquisition_date.isoformat(),body.ground_resolution_m,
          body.crs,json.dumps(body.bounding_box),body.review_note.strip(),actor['id'],core.iso_now()))
    core.write_audit(actor['id'],'satellite_metadata_review','case',case_id,ident)
    return {'id':ident,'metadataStored':True,'rasterDownloaded':False,
       'imageLicensingIndependentlyConfirmed':False}

@router.get('/api/cases/{case_id}/licensed-satellite-references')
def satellite_references(case_id:str,actor=Depends(core.actor_from_cookie)):
    with db.connect() as conn:
        core.case_or_404(conn,case_id,actor)
        rows=[dict(x) for x in conn.execute(
         'SELECT id,evidence_id,provider,source_url,rights_url,acquisition_date,'
         'ground_resolution_m,crs,bounds_json FROM licensed_satellite_observations '
         'WHERE case_id=? ORDER BY acquisition_date DESC,id DESC LIMIT 50',(case_id,))]
    return {'items':rows,'hasRasterLayer':False,'layerEnabled':False,
        'notice':'Licensed metadata reference only. No satellite tile, coverage or current resolution was independently fetched.'}
