"""Bouwt statische ski-test-pagina's uit de database. Alles onder /ski-test/ (één pad = makkelijk uit te zetten).
Gebruik: python site/build.py /var/www/skitest"""
import os, sys, re, json, unicodedata, psycopg2
from jinja2 import Environment, FileSystemLoader
DSN = os.environ.get("SKIDATA_DSN", "dbname=skidata user=skidata password=skidata_local host=localhost")
BASE = "/ski-test"
ASSEN = [("grip","Grip & carving"),("wendbaarheid","Wendbaarheid"),("stabiliteit","Stabiliteit op snelheid"),
         ("drijfvermogen","Drijfvermogen (poeder)"),("speelsheid","Speelsheid"),("vergevingsgezind","Vergevingsgezindheid"),("gewicht","Licht gewicht")]
CAT = {"allmountain": "Allmountain"}
NIVEAU = {"Beginner-Intermediate":"Beginner tot gemiddeld","Intermediate-Advanced":"Gemiddeld tot gevorderd","Advanced-Expert":"Gevorderd tot expert","Intermediate":"Gemiddeld","Advanced":"Gevorderd","Expert":"Expert"}
VERTAAL = {"wood":"hout","metal":"metaal","carbon":"carbon","fiberglass":"glasvezel","basalt":"basalt","flax":"vlas",
  "partial twin tip":"half-twintip","full twin tip":"twintip","twin tip":"twintip","flat tail":"vlakke staart",
  "rocker/camber/rocker":"rocker – camber – rocker","tip & tail rocker":"rocker in tip en staart, camber in het midden",
  "rocker/camber":"rocker voor, camber achter","camber":"camber","full rocker":"volledige rocker"}
def nl(v):
    if not v: return None
    v = v.split(":")[0].strip()
    return ", ".join(VERTAAL.get(x.strip().lower(), x.strip()) for x in v.split(",")) if "," in v else VERTAAL.get(v.lower(), v)
def slug(*d):
    s = unicodedata.normalize("NFKD", " ".join(d)).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","-",s).strip("-")
def laden():
    con = psycopg2.connect(DSN); cur = con.cursor()
    cur.execute("""SELECT s.id,m.naam,s.model,s.seizoen,s.categorie,s.geslacht,s.niveau,s.profiel,s.constructie,s.tail_type,
      sc.grip,sc.wendbaarheid,sc.stabiliteit,sc.drijfvermogen,sc.speelsheid,sc.vergevingsgezind,sc.gewicht,sc.methode_versie
      FROM ski s JOIN merk m ON m.id=s.merk_id LEFT JOIN score sc ON sc.ski_id=s.id ORDER BY m.naam,s.model""")
    ski = []
    for r in cur.fetchall():
        d = dict(zip(["id","merk","model","seizoen","categorie","geslacht","niveau","profiel","constructie","tail_type",
                      "grip","wendbaarheid","stabiliteit","drijfvermogen","speelsheid","vergevingsgezind","gewicht","versie"], r))
        cur.execute("SELECT lengte_cm,tip_mm,taille_mm,tail_mm,radius_m,gewicht_g FROM ski_lengte WHERE ski_id=%s ORDER BY lengte_cm",(d["id"],))
        d["lengtes"] = [dict(zip(["lengte","tip","taille","tail","radius","gewicht"],x)) for x in cur.fetchall()]
        d["taille"] = d["lengtes"][len(d["lengtes"])//2]["taille"] if d["lengtes"] else None
        for k in ("profiel","constructie","tail_type"): d[k+"_nl"] = nl(d[k])
        d["naam"] = f'{d["merk"]} {d["model"]}'
        d["slug"] = slug(d["merk"], d["model"], d["seizoen"].replace("/","-"))
        d["merk_slug"] = slug(d["merk"])
        d["niveau_nl"] = NIVEAU.get(d["niveau"], d["niveau"] or "–")
        d["scores"] = [(k, label, d[k]) for k, label in ASSEN]
        ski.append(d)
    return ski
def main(out):
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")), autoescape=True)
    ski = laden(); merken = sorted({s["merk"] for s in ski})
    def schrijf(pad, tpl, **kw):
        p = os.path.join(out, pad.strip("/"), "index.html"); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(env.get_template(tpl).render(BASE=BASE, ASSEN=ASSEN, **kw))
    finder = [dict(n=s["naam"], u=f'{BASE}/{s["slug"]}/', t=s["taille"], niv=s["niveau"] or "", g=s["geslacht"],
                   **{k: s[k] for k,_ in ASSEN}) for s in ski]
    schrijf(BASE, "index.html", ski=ski, merken=merken, finder=json.dumps(finder, ensure_ascii=False), titel="Ski-test 2026/27")
    schrijf(f"{BASE}/methode", "methode.html", titel="Zo beoordelen wij ski's")
    for c, cn in CAT.items():
        lijst = sorted([s for s in ski if s["categorie"] == c], key=lambda s: -sum((s[k] or 0) for k,_ in ASSEN))
        schrijf(f"{BASE}/{c}", "lijst.html", ski=lijst, titel=f"{cn}-ski's 2026/27", intro=f"Alle {cn.lower()}-ski's van seizoen 2026/27 die we in de database hebben, met onze scores.")
    for m in merken:
        lijst = [s for s in ski if s["merk"] == m]
        schrijf(f"{BASE}/{slug(m)}", "lijst.html", ski=lijst, titel=f"Alle {m}-ski's 2026/27", intro=f"Alle ski's van {m} uit seizoen 2026/27 in onze database.")
    for s in ski:
        schrijf(f'{BASE}/{s["slug"]}', "ski.html", s=s, titel=f'{s["naam"]} ({s["seizoen"]}) – test & specs')
    print(len(ski), "ski-pagina's,", len(merken), "merkpagina's gebouwd in", out)
if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "/var/www/skitest")
