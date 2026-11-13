"""Scraper voor spec-tabellen (evo.com). Specs zijn feiten; we nemen geen teksten of oordelen over.
Gebruik: python scrapers/evo.py urls.txt [categorie]"""
import asyncio, re, sys, os
import psycopg2
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
DSN = os.environ.get("SKIDATA_DSN", "dbname=skidata user=skidata password=skidata_local host=localhost")

def veld(t, naam):
    m = re.search(rf"{re.escape(naam)}:\s*\n(.+)", t)
    return m.group(1).strip() if m else None

def seizoen(titel):
    m = re.search(r"(20\d\d)\s*$", titel)
    if not m: return None
    j = int(m.group(1)); return f"{j-1}/{str(j)[2:]}"

def parse(titel, t, url, categorie):
    mt = re.match(r"(\S+)\s+(.+?)\s+Skis(?:\s*-\s*(Women's|Men's))?\s+(20\d\d)$", titel.strip())
    if not mt: return None
    merk, model, gesl, jaar = mt.groups()
    rijen = []
    i = t.find("SIZE\tTIP WIDTH")
    if i >= 0:
        kop = t[i:].split("\n")[0].split("\t")
        for regel in t[i:].split("\n")[1:]:
            d = regel.split("\t")
            if not d or not re.match(r"^\d{2,3}$", d[0].strip()): break
            r = dict(zip(kop, [x.strip() for x in d]))
            rad = r.get("TURNING RADIUS", "")
            nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", rad)]
            rad = nums[len(nums)//2] if nums else None
            def num(k):
                v = r.get(k, ""); return int(float(v)) if re.match(r"^\d+(\.\d+)?$", v) else None
            rijen.append(dict(lengte=int(d[0]), tip=num("TIP WIDTH"), taille=num("WAIST WIDTH"),
                              tail=num("TAIL WIDTH"), radius=rad, gewicht=num("INDIV. SKI WEIGHT")))
    return dict(merk=merk, model=model, geslacht={"Women's": "dames", "Men's": "heren"}.get(gesl, "unisex"),
                seizoen=seizoen(titel), categorie=categorie, niveau=veld(t, "Ability Level"),
                profiel=veld(t, "Rocker Type"), constructie=veld(t, "Core/Laminates"),
                tail_type=veld(t, "Tail Type"), url=url, lengtes=rijen)

def opslaan(cur, s):
    cur.execute("INSERT INTO merk(naam) VALUES (%s) ON CONFLICT (naam) DO NOTHING", (s["merk"],))
    cur.execute("SELECT id FROM merk WHERE naam=%s", (s["merk"],)); mid = cur.fetchone()[0]
    cur.execute("""INSERT INTO ski(merk_id,model,seizoen,categorie,geslacht,niveau,profiel,constructie,tail_type,bron_url,bijgewerkt)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (merk_id,model,seizoen) DO UPDATE SET categorie=EXCLUDED.categorie, geslacht=EXCLUDED.geslacht,
        niveau=EXCLUDED.niveau, profiel=EXCLUDED.profiel, constructie=EXCLUDED.constructie, tail_type=EXCLUDED.tail_type,
        bron_url=EXCLUDED.bron_url, bijgewerkt=now() RETURNING id""",
        (mid, s["model"], s["seizoen"], s["categorie"], s["geslacht"], s["niveau"], s["profiel"], s["constructie"], s["tail_type"], s["url"]))
    sid = cur.fetchone()[0]
    for l in s["lengtes"]:
        cur.execute("""INSERT INTO ski_lengte(ski_id,lengte_cm,tip_mm,taille_mm,tail_mm,radius_m,gewicht_g) VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (ski_id,lengte_cm) DO UPDATE SET tip_mm=EXCLUDED.tip_mm,taille_mm=EXCLUDED.taille_mm,tail_mm=EXCLUDED.tail_mm,
            radius_m=EXCLUDED.radius_m,gewicht_g=COALESCE(EXCLUDED.gewicht_g,ski_lengte.gewicht_g)""",
            (sid, l["lengte"], l["tip"], l["taille"], l["tail"], l["radius"], l["gewicht"]))

async def main(urls, categorie):
    con = psycopg2.connect(DSN); cur = con.cursor()
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(user_agent=UA)
        for u in urls:
            try:
                await pg.goto(u, timeout=45000); await pg.wait_for_timeout(2000)
                titel = (await pg.inner_text("h1")).strip(); t = await pg.inner_text("body")
                s = parse(titel, t, u, categorie)
                if not s or not s["lengtes"]: print("OVERGESLAGEN", u, titel); continue
                opslaan(cur, s); con.commit(); print("OK", s["merk"], s["model"], s["seizoen"], len(s["lengtes"]), "lengtes")
            except Exception as e:
                con.rollback(); print("FOUT", u, e)
            await asyncio.sleep(2)
        await b.close()

if __name__ == "__main__":
    urls = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
    asyncio.run(main(urls, sys.argv[2] if len(sys.argv) > 2 else "allmountain"))
