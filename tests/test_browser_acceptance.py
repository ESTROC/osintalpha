"""P1-091 genuine Chromium browser acceptance, including 390px mobile screenshots.

Run with OSINTALPHA_BROWSER_BASE. This suite is skipped by ordinary unit
pytest when no actual browser/server is present; a dedicated CI job runs it.
"""
import os
from pathlib import Path
import pytest

def test_chromium_auth_case_report_keyboard_and_mobile():
    browser_base=os.getenv('OSINTALPHA_BROWSER_BASE')
    if not browser_base:
        pytest.skip('Dedicated Playwright browser job starts an actual HTTP server.')
    sync_api=pytest.importorskip('playwright.sync_api')
    out=Path('artifacts/browser');out.mkdir(parents=True,exist_ok=True)
    with sync_api.sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':900},device_scale_factor=1)
        page=context.new_page()
        response=page.goto(browser_base,wait_until='domcontentloaded')
        assert response and response.status==200
        page.locator('#login-form input[name="username"]').fill('admin')
        page.locator('#login-form input[name="password"]').fill(os.environ['OSINTALPHA_ADMIN_PASSWORD'])
        page.locator('#login-form button').click()
        page.locator('#smart-query').wait_for(timeout=15000)
        assert page.get_by_text('Search public sources').count()>=1
        api=context.request.post(browser_base+'/api/cases',
            headers={'X-OSINT-Alpha-Action':'1'},
            data={'title':'Browser acceptance synthetic case','subject_type':'organization',
              'query':'Example Research Institute','purpose':'Authorized synthetic test of public web research',
              'authority_confirmed':True})
        assert api.status==201,api.text()
        case_id=api.json()['id']
        page.reload(wait_until='domcontentloaded')
        page.locator('button[data-open="'+case_id+'"]').first.click()
        page.get_by_text('CASE ANSWER · PROVENANCE FIRST').wait_for(timeout=15000)
        assert page.get_by_text('Sortable, filterable public-source leads').count()>=1
        page.screenshot(path=str(out/'case-desktop.png'),full_page=True)
        page.locator('button[data-tab="overview"]').focus()
        page.keyboard.press('Tab')
        focus=page.evaluate("document.activeElement?.tagName?.toLowerCase()")
        assert focus in ('button','a','input','select','summary','textarea')
        report=context.request.get(browser_base+'/api/cases/'+case_id+'/report.html')
        assert report.status==200,report.text()
        assert 'Example Research Institute' in report.text()
        page.set_viewport_size({'width':390,'height':844})
        page.reload(wait_until='domcontentloaded')
        page.get_by_text('CASE ANSWER · PROVENANCE FIRST').wait_for(timeout=15000)
        assert page.locator('button[data-tab="overview"]').count()==1
        page.screenshot(path=str(out/'case-mobile.png'),full_page=True)
        browser.close()
