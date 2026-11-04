import os, sys, asyncio
from playwright.async_api import async_playwright
URL=sys.argv[1]; SHOT=sys.argv[2]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/local/bin/google-chrome"); pg=await b.new_page(viewport={"width":1400,"height":1100})
        errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL)
        await pg.fill("#user",os.environ["E3_VAULT_USER"]); await pg.fill("#pass",os.environ["E3_VAULT_PASS"]); await pg.click("#form button")
        await pg.wait_for_selector("#nav a",timeout=60000); await pg.wait_for_timeout(2000)
        t=await pg.inner_text("body"); print("92.4" in t, "Marca 37" in t or "MARCA 37" in t)
        for r in await pg.query_selector_all("table tbody tr"):
            if "6000000306" in await r.inner_text(): await r.scroll_into_view_if_needed(); await r.click(); break
        await pg.wait_for_timeout(1500)
        t=await pg.inner_text("body"); i=t.rfind("funcionario_nombre"); print(t[i:i+150].replace("\n"," | "))
        await pg.locator("td", has_text="funcionario_nombre").last.scroll_into_view_if_needed(); await pg.wait_for_timeout(400)
        await pg.screenshot(path=SHOT); print("errors", errs)
        await b.close()
asyncio.run(main())
