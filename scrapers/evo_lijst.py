"""Verzamelt productlinks uit een evo-categorie (alleen ski's zonder binding, gekozen modeljaar).
Gebruik: python scrapers/evo_lijst.py <categorie-url> <jaar> <max_paginas> > lijst.txt"""
import asyncio, sys, re
from playwright.async_api import async_playwright
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
async def main(base, jaar, n):
    gezien = set()
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(user_agent=UA)
        for i in range(1, n+1):
            u = base if i == 1 else f"{base}?page={i}"
            r = await pg.goto(u, timeout=45000)
            if r.status != 200: break
            await pg.wait_for_timeout(2000)
            links = await pg.eval_on_selector_all("a[href*=\"/products/\"]", "els=>els.map(e=>e.href.split(\"?\")[0])")
            nieuw = 0
            for l in links:
                if l in gezien: continue
                if not l.endswith(f"-skis-{jaar}") and not re.search(rf"-skis-women-s-{jaar}$", l): continue
                if re.search(r"bindings|kids|junior|youth|boys|girls", l): continue
                gezien.add(l); nieuw += 1; print(l, flush=True)
            
            await asyncio.sleep(1.5)
        await b.close()
asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3])))
