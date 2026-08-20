
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 900})
        await page.goto('http://localhost:3000', wait_until='networkidle')
        await page.wait_for_timeout(2000)
        await page.screenshot(path=r'D:\code\video-note\screenshot.png', full_page=True)
        await browser.close()
        print('screenshot saved')

asyncio.run(main())
