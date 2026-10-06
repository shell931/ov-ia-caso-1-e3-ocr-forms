import os, sys, asyncio
from playwright.async_api import async_playwright
URL=sys.argv[1]; SHOT=sys.argv[2]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/local/bin/google-chrome")
        pg = await b.new_page(viewport={"width":1400,"height":1100})
        errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL)
        await pg.fill("#user", os.environ["E3_VAULT_USER"]); await pg.fill("#pass", os.environ["E3_VAULT_PASS"])
        await pg.click("#form button")
        await pg.wait_for_selector("#nav a", timeout=60000)
        await pg.wait_for_timeout(2500)
        print([await a.inner_text() for a in await pg.query_selector_all("#nav a")][-2:])
        txt = await pg.inner_text("body")
        print("93.3" in txt, "funcionario" in txt.lower())
        print("errors", errs)
        await pg.screenshot(path=SHOT)
        await b.close()
asyncio.run(main())
