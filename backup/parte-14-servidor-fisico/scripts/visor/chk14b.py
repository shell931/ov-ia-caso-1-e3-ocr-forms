import os, sys, asyncio
from playwright.async_api import async_playwright
URL=sys.argv[1]; PRE=sys.argv[2]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/local/bin/google-chrome")
        pg = await b.new_page(viewport={"width":1400,"height":1100})
        await pg.goto(URL)
        await pg.fill("#user", os.environ["E3_VAULT_USER"]); await pg.fill("#pass", os.environ["E3_VAULT_PASS"])
        await pg.click("#form button")
        await pg.wait_for_selector("#nav a", timeout=60000)
        await pg.wait_for_timeout(2500)
        navs=[await a.inner_text() for a in await pg.query_selector_all("#nav a")]
        print(navs[-1:], len(navs))
        rows = await pg.query_selector_all("table tbody tr")
        print("rows", len(rows))
        cand = [r for r in rows if "6000000030" in (await r.inner_text())]
        tgt = cand[0] if cand else rows[-1]
        await tgt.scroll_into_view_if_needed(); await tgt.click(); await pg.wait_for_timeout(2000)
        txt=await pg.inner_text("body")
        i=txt.find("funcionario_cedula"); print("detalle:", txt[i:i+60].replace("\n"," | ") if i>=0 else "NO")
        await pg.screenshot(path=PRE+"_detalle.png", full_page=False)
        await b.close()
asyncio.run(main())
