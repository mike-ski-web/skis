"""Bouwt de ski-test-pagina's uit de database + redactionele content (content/reviews/<slug>.json).
- Eén pad: /ski-test/ (makkelijk aan/uit).
- Webadressen ZONDER seizoen: een ski houdt elk jaar dezelfde pagina; seizoenen staan op die pagina.
Gebruik: python site/build.py /var/www/skitest"""
import os, sys, re, json, math, unicodedata, datetime, psycopg2
from jinja2 import Environment, FileSystemLoader
DSN = os.environ.get("SKIDATA_DSN", "dbname=skidata user=skidata password=skidata_local host=localhost")
BASE = "/ski-test"
HIER = os.path.dirname(os.path.abspath(__file__))
REVIEWS = os.path.join(HIER, "..", "content", "reviews")
ASSEN = [("grip","Grip op harde piste"),("wendbaarheid","Wendbaarheid"),("stabiliteit","Stabiliteit op snelheid"),
         ("drijfvermogen","Drijfvermogen in poeder"),("speelsheid","Speelsheid"),("vergevingsgezind","Vergevingsgezind"),("gewicht","Licht gewicht")]
CAT = {"allmountain": ("Allmountain", "Ski's voor de hele berg: op de piste en ernaast. De meest gekozen categorie voor een wintersportweek.")}
NIVEAU = {"Beginner-Intermediate":"Beginner tot gemiddeld","Intermediate-Advanced":"Gemiddeld tot gevorderd","Advanced-Expert":"Gevorderd tot expert",
          "Beginner":"Beginner","Intermediate":"Gemiddeld","Advanced":"Gevorderd","Expert":"Expert"}
VERTAAL = {"wood":"hout","metal":"metaal","carbon":"carbon","fiberglass":"glasvezel","basalt":"basalt","flax":"vlas","foam":"schuim",
  "partial twin tip":"half-twintip","full twin tip":"twintip","twin tip":"twintip","flat tail":"vlakke staart","flat":"vlakke staart",
  "rocker/camber/rocker":"rocker – camber – rocker","tip & tail rocker":"rocker in tip en staart, camber in het midden",
  "rocker/camber":"rocker voor, camber achter","tip rocker":"rocker in de tip, camber eronder","camber":"camber","full rocker":"volledige rocker","all mountain rocker":"lichte rocker in de tip, camber eronder","early rise":"lichte rocker in de tip, camber eronder","rocker/flat/rocker":"rocker – vlak – rocker","flat":"vlak","hybrid camber":"camber met rocker in tip en staart","freestyle rocker":"rocker in tip en staart (freestyle)","directional rocker":"rocker in de tip, camber eronder"}
def nl(v):
    if not v: return None
    v = v.split(":")[0].strip()
    return ", ".join(VERTAAL.get(x.strip().lower(), x.strip()) for x in v.split(","))
def slug(*d):
    s = unicodedata.normalize("NFKD", " ".join(d)).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","-",s).strip("-")
def woord(v):
    return "uitstekend" if v>=9 else "sterk" if v>=7 else "gemiddeld" if v>=5 else "beperkt" if v>=3 else "zwak"

def silhouet(l):
    """SVG bovenaanzicht van de ski (breedte overdreven weergegeven) op basis van tip/taille/tail."""
    if not (l and l.get("tip") and l.get("taille") and l.get("tail")): return ""
    L = 600; k = 0.2; c = 36
    tip, mid, tail = l["tip"]*k, l["taille"]*k, l["tail"]*k
    pts = [(0, tail*0.55), (12, tail*0.92), (40, tail), (L*0.46, mid), (L*0.82, tip), (L*0.92, tip*0.8), (L*0.98, tip*0.35), (L, 0)]
    boven = " ".join(f"{x:.0f},{c-y:.1f}" for x, y in pts); onder = " ".join(f"{x:.0f},{c+y:.1f}" for x, y in reversed(pts))
    return (f'<figure class="sil"><svg viewBox="-4 0 610 92" class="silhouet" role="img" aria-label="Vorm van de ski van boven gezien">'
            f'<polygon points="{boven} {onder}"/>'
            f'<text x="20" y="88">staart {l["tail"]} mm</text><text x="{L*0.46-40:.0f}" y="88">taille {l["taille"]} mm</text>'
            f'<text x="{L*0.82-30:.0f}" y="88">tip {l["tip"]} mm</text></svg>'
            f'<figcaption>Vorm van boven (breedte overdreven) · {l["lengte"]} cm · draaistraal {l["radius"] or "–"} m</figcaption></figure>')

def laden():
    con = psycopg2.connect(DSN); cur = con.cursor()
    cur.execute("""SELECT s.id,m.naam,s.model,s.seizoen,s.categorie,s.geslacht,s.niveau,s.profiel,s.constructie,s.tail_type,
      sc.grip,sc.wendbaarheid,sc.stabiliteit,sc.drijfvermogen,sc.speelsheid,sc.vergevingsgezind,sc.gewicht,sc.methode_versie
      FROM ski s JOIN merk m ON m.id=s.merk_id LEFT JOIN score sc ON sc.ski_id=s.id ORDER BY m.naam,s.model,s.seizoen DESC""")
    per = {}
    for r in cur.fetchall():
        d = dict(zip(["id","merk","model","seizoen","categorie","geslacht","niveau","profiel","constructie","tail_type",
                      "grip","wendbaarheid","stabiliteit","drijfvermogen","speelsheid","vergevingsgezind","gewicht","versie"], r))
        cur.execute("SELECT lengte_cm,tip_mm,taille_mm,tail_mm,radius_m,gewicht_g FROM ski_lengte WHERE ski_id=%s ORDER BY lengte_cm",(d["id"],))
        d["lengtes"] = [dict(zip(["lengte","tip","taille","tail","radius","gewicht"],x)) for x in cur.fetchall()]
        if not d["lengtes"]: continue
        d["ref"] = d["lengtes"][len(d["lengtes"])//2]
        d["taille"] = d["ref"]["taille"]
        for k in ("profiel","constructie","tail_type"): d[k+"_nl"] = nl(d[k])
        d["niveau_nl"] = NIVEAU.get(d["niveau"], d["niveau"] or "–")
        d["scores"] = [(k, label, d[k] or 0, woord(d[k] or 0)) for k, label in ASSEN]
        d["totaal"] = sum(d[k] or 0 for k,_ in ASSEN)
        key = slug(d["merk"], d["model"])
        per.setdefault(key, []).append(d)
    ski = []
    for key, versies in per.items():
        huidig = versies[0]
        s = dict(huidig); s["slug"] = key; s["merk_slug"] = slug(s["merk"]); s["naam"] = f'{s["merk"]} {s["model"]}'
        s["eerder"] = versies[1:]; s["svg"] = silhouet(s["ref"])
        cur.execute("""SELECT a.winkel, a.prijs, a.op_voorraad, a.deeplink FROM aanbieding a JOIN ski x ON x.id=a.ski_id JOIN merk m ON m.id=x.merk_id
                       WHERE m.naam=%s AND x.model=%s AND a.deeplink IS NOT NULL ORDER BY a.op_voorraad DESC, a.prijs""", (s["merk"], s["model"]))
        s["winkels"] = [dict(winkel=w, prijs=p, voorraad=v, link=l) for w, p, v, l in cur.fetchall()]
        p = os.path.join(REVIEWS, key + ".json")
        s["review"] = json.load(open(p)) if os.path.exists(p) else None
        if not s["review"]:
            top = sorted(s["scores"], key=lambda x: -x[2])[:2]
            breed = "smalle" if (s["taille"] or 95) < 88 else "brede" if (s["taille"] or 95) >= 100 else "veelzijdige"
            s["auto"] = f'Een {breed} {CAT.get(s["categorie"],("ski",))[0].lower()}-ski ({s["taille"]} mm onder de voet) die op basis van de specificaties vooral sterk is in {top[0][1].lower()} en {top[1][1].lower()}. Bedoeld voor: {s["niveau_nl"].lower()}.'
        ski.append(s)
    for s in ski:
        v = [s[k] or 0 for k,_ in ASSEN]
        s["lijkt"] = sorted((x for x in ski if x is not s and x["categorie"] == s["categorie"]),
                            key=lambda x: math.dist(v, [x[k] or 0 for k,_ in ASSEN]))[:3]
    return ski

def main(out):
    env = Environment(loader=FileSystemLoader(os.path.join(HIER, "templates")), autoescape=True)
    env.filters["tojson_nl"] = lambda x: json.dumps(x, ensure_ascii=False)
    ski = laden(); merken = sorted({(s["merk"], s["merk_slug"]) for s in ski})
    seizoen = max(s["seizoen"] for s in ski)
    nu = datetime.date.today().strftime("%d-%m-%Y")
    g = dict(BOUWDATUM=datetime.date.today().isoformat(), LIVE=bool(os.environ.get("SKIDATA_LIVE")), BASE=BASE, ASSEN=ASSEN, SEIZOEN=seizoen, BIJGEWERKT=nu, CAT=CAT)
    def schrijf(pad, tpl, **kw):
        p = os.path.join(out, pad.strip("/"), "index.html"); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(env.get_template(tpl).render(**g, **kw))
    def mini(s): return dict(n=s["naam"], u=f'{BASE}/{s["slug"]}/', t=s["taille"], niv=s["niveau"] or "", g=s["geslacht"],
                             r=bool(s["review"]), p=bool(s["winkels"]), tot=s["totaal"], **{k: s[k] or 0 for k,_ in ASSEN})
    schrijf(BASE, "index.html", ski=ski, merken=merken, finder=[mini(s) for s in ski],
            uitgelicht=[s for s in ski if s["review"]], titel=f"Ski-test {seizoen}: vind de ski die bij je past")
    schrijf(f"{BASE}/methode", "methode.html", titel="Zo testen en beoordelen wij ski's")
    for c, (cn, intro) in CAT.items():
        lijst = sorted([s for s in ski if s["categorie"] == c], key=lambda s: (-bool(s["review"]), -s["totaal"]))
        schrijf(f"{BASE}/{c}", "lijst.html", ski=lijst, data=[mini(s) for s in lijst], titel=f"De beste {cn.lower()}-ski's van {seizoen}", intro=intro)
    for m, ms in merken:
        lijst = [s for s in ski if s["merk"] == m]
        schrijf(f"{BASE}/{ms}", "lijst.html", ski=lijst, data=[mini(s) for s in lijst], titel=f"Alle {m}-ski's van {seizoen}", intro=f"Alle ski's van {m} uit seizoen {seizoen} in onze database, met specificaties en onze beoordeling.")
    for s in ski:
        schrijf(f'{BASE}/{s["slug"]}', "ski.html", s=s, titel=f'{s["naam"]} review & test ({s["seizoen"]})')
    import shutil; os.makedirs(os.path.join(out, BASE.strip("/"), "assets"), exist_ok=True)
    shutil.copy(os.path.join(HIER, "static", "logo.png"), os.path.join(out, BASE.strip("/"), "assets", "logo.png"))
    print(len(ski), "ski-pagina's,", len(merken), "merken,", sum(1 for s in ski if s["review"]), "met review →", out)
if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else "/var/www/skitest")
