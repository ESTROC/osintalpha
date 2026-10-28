"""P2-135 a genuine Chromium mobile, keyboard and case-load request baseline."""
import os,json
from pathlib import Path
import pytest
def test_mobile_accessibility_and_initial_request_count():
    base=os.getenv('OSINTALPHA_BROWSER_BASE')
    if not base:pytest.skip('Dedicated Chromium CI required')
    api=pytest.importorskip('playwright.sync_api')
    with api.sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':390,'height':844})
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base,wait_until='domcontentloaded')
        page.locator('#login-form input[name="username"]').fill('admin')
        page.locator('#login-form input[name="password"]').fill(os.environ['OSINTALPHA_ADMIN_PASSWORD'])
        page.locator('#login-form button').click()
        page.locator('#smart-query').wait_for(timeout=15000)
        tags=[]
        for i in range(8):
            page.keyboard.press('Tab')
            tags.append(page.evaluate("document.activeElement?.tagName?.toLowerCase()||''"))
        assert sum(x in ('button','a','input','select','textarea') for x in tags)>=4,tags
        creation=context.request.post(base+'/api/cases',headers={'X-OSINT-Alpha-Action':'1'},data={
          'title':'Accessibility synthetic case','subject_type':'organization','query':'Public Example Institute',
          'purpose':'Authorized synthetic test for browser accessibility',
          'authority_confirmed':True})
        assert creation.status==201,creation.text()
        case=creation.json()['id']
        requests=[]
        page.on('request',lambda r:requests.append(r.url) if '/api/' in r.url else None)
        page.goto(base+'/?case='+case,wait_until='domcontentloaded')
        page.get_by_text('CASE ANSWER · PROVENANCE FIRST').wait_for(timeout=15000)
        assert len([url for url in requests if '/initial-view' in url])==1,requests
        assert len(requests)<=9,requests
        layout=page.evaluate("({lang:document.documentElement.lang,width:innerWidth,scroll:document.documentElement.scrollWidth,title:document.title})")
        assert layout['lang']=='en' and layout['title']
        assert layout['scroll']<=layout['width']+110,layout
        assert not errors,errors
        out=Path('artifacts/browser');out.mkdir(parents=True,exist_ok=True)
        (out/'mobile-baseline.json').write_text(json.dumps({'layout':layout,'apiRequests':len(requests),
           'keyboardTargets':tags,'isWCAGCertification':False},indent=2))
        page.screenshot(path=str(out/'mobile-review-baseline.png'),full_page=True)
        browser.close()
