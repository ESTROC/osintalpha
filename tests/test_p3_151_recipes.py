"""P3 151 procedure versioning, ownership, preview and no automatic personal monitoring."""
def test_saved_recipe_preview_and_revision(client,auth):
    saved=client.post('/api/research/recipes',headers=auth,json={
      'title':'Official institution publications','description':'Synthetic procedure',
      'question':'Locate public organization releases and source citations'})
    assert saved.status_code==201,saved.text
    id=saved.json()['id']
    preview=client.get(f'/api/research/recipes/{id}/preview?subject_type=organization&country=IN')
    assert preview.status_code==200,preview.text
    assert preview.json()['country']=='IN'
    assert not preview.json()['automaticRecurringSearch']
    edit={'expected_version':1,'title':'Official public notices',
        'description':'Review published sources','question':'Find official organization announcements and registered disclosures'}
    updated=client.put(f'/api/research/recipes/{id}',headers=auth,json=edit)
    assert updated.status_code==200,updated.text
    assert updated.json()['version']==2
    assert client.put(f'/api/research/recipes/{id}',headers=auth,json=edit).status_code==409
    prev=client.get(f'/api/research/recipes/{id}/preview')
    assert prev.json()['version']==2
    assert prev.json()['quotaRemaining'] is None
