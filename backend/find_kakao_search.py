import asyncio, sys, json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def intercept():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
            locale='ko-KR', viewport={'width': 390, 'height': 844})
        page = await context.new_page()

        captured = []
        async def on_req(req):
            if 'kakao.golf/api' in req.url and req.method == 'POST':
                captured.append({'url': req.url, 'body': req.post_data})
        async def on_resp(resp):
            if 'kakao.golf/api' in resp.url and resp.status == 200:
                try:
                    text = await resp.text()
                    for c in captured:
                        if c['url'] == resp.url and 'resp' not in c:
                            c['resp'] = text
                except: pass

        page.on('request', on_req)
        page.on('response', on_resp)

        url = 'https://www.kakao.golf/tee-time?date=20260425&area=2&sort=price'
        print(f'Loading: {url}')
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(4000)

        search_calls = [c for c in captured if 'tee-time/search' in c['url']]
        print(f'\ntee-time/search calls: {len(search_calls)}')
        for c in search_calls:
            body = json.loads(c.get('body', '{}'))
            print(f'\n=== 실제 검색 바디 ===')
            print(json.dumps(body, ensure_ascii=False, indent=2))
            resp_data = json.loads(c.get('resp', '{}'))
            lst = resp_data.get('list', [])
            seqs = [i.get('golfInfoSeq') for i in lst]
            print(f'\n결과: {len(lst)}개, 159포함={159 in seqs}')
            print(f'seqs: {seqs[:10]}')

        await browser.close()

asyncio.run(intercept())
