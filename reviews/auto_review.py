"""Schrijft automatisch reviews per ski met Claude (Anthropic API + webzoeken).
- Zoekt per ski de belangrijke internationale tests, vat ze samen in eigen woorden, noemt bronnen bij naam (geen links).
- Neemt ook alles uit inbox/ mee dat over deze ski gaat.
- Schrijft content/reviews/<slug>.json met "status": "concept" (redactie kan op "goedgekeurd" zetten).
- Bestaande goedgekeurde reviews worden niet overschreven.
Gebruik: python reviews/auto_review.py [--max 20] [--slug volkl-mantra-102] [--opnieuw]
Config (/opt/skidata/.env): ANTHROPIC_API_KEY, SKIDATA_MODEL (optioneel), SKIDATA_WEBSEARCH (optioneel)"""
import os, sys, json, re, glob, argparse, datetime, psycopg2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "site"))
from build import slug, NIVEAU  # zelfde slugs als de site
HIER = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HIER, "..")
OUT = os.path.join(ROOT, "content", "reviews"); INBOX = os.path.join(ROOT, "inbox")
DSN = os.environ.get("SKIDATA_DSN", "dbname=skidata user=skidata password=skidata_local host=localhost")
MODEL = os.environ.get("SKIDATA_MODEL", "claude-opus-5-5")
WEBSEARCH = os.environ.get("SKIDATA_WEBSEARCH", "web_search_20250305")

INSTRUCTIE = """Je bent de ski-testredactie van Skiinformatie.nl. Schrijf een review van één ski in helder, warm Nederlands voor wintersporters.
Werkwijze:
1. Zoek met de zoektool de belangrijkste onafhankelijke tests en reviews van DEZE ski en DIT seizoen (en de vorige versie als hij ongewijzigd is). Denk aan Ski Essentials, Blister, Freeskier, Ski Magazine, OutdoorGearLab, Powder7, Forecast Ski Test, Skimagazin, Schneehoehen/snow-online, Skitalk. Gebruik minimaal twee onafhankelijke bronnen als die bestaan.
2. Controleer of de ski dit seizoen veranderd is (constructie, vorm, naam) of alleen nieuwe graphics heeft. Zeg het als tests over een vorige versie gaan.
3. Vat samen wat de testers vinden, in je EIGEN woorden. Noem de bron bij naam ("Ski Essentials vindt...", "Volgens Blister..."). Nooit letterlijk citeren, nooit links of URL's in de tekst.
4. Geef daarna een eigen, duidelijk oordeel: voor wie wel, voor wie niet. Waar bronnen elkaar tegenspreken, zeg dat.
5. Verzin niets. Kun je te weinig vinden, zeg dat eerlijk in het verhaal en houd het kort.
Stijl: schrijf "piste", niet "baan". Korte zinnen, geen marketingtaal, geen superlatieven zonder onderbouwing.
Antwoord uitsluitend met één JSON-object (geen andere tekst), met deze velden:
{"kort": "1 zin typering", "verhaal": ["alinea 1: wat is er nieuw / wat is het voor ski", "alinea 2: wat testers zeggen, met bronnamen", "alinea 3: ons oordeel"],
 "goed": ["2-4 korte punten"], "minder": ["2-4 korte punten"], "voorwie": "1-2 zinnen", "bronnen": ["namen van gebruikte bronnen, bv. 'Ski Essentials (test 2026/27)'"],
 "veranderd_dit_seizoen": "ja/nee/onbekend + 1 korte toelichting"}"""

def specs_tekst(cur, sid):
    cur.execute("SELECT lengte_cm,tip_mm,taille_mm,tail_mm,radius_m,gewicht_g FROM ski_lengte WHERE ski_id=%s ORDER BY lengte_cm", (sid,))
    return "; ".join(f"{l}cm {t}/{w}/{ta} mm r={r}m" + (f" {g}g" if g else "") for l,t,w,ta,r,g in cur.fetchall())

def inbox_voor(sl, naam):
    stukken = []
    for p in glob.glob(os.path.join(INBOX, "*")):
        if os.path.isdir(p) or p.endswith("README.md"): continue
        try: t = open(p, errors="ignore").read()
        except Exception: continue
        if sl in os.path.basename(p) or naam.lower() in t.lower():
            stukken.append(f"--- {os.path.basename(p)} ---\n{t[:4000]}")
    return "\n".join(stukken)

def schrijf_review(client, ski, cur):
    sid, merk, model, seizoen, niveau, profiel, constructie = ski
    naam = f"{merk} {model}"; sl = slug(merk, model)
    vraag = (f"Ski: {naam}\nSeizoen: {seizoen} (Amerikaanse webshops noemen dit modeljaar {int(seizoen[:4])+1})\n"
             f"Niveau volgens fabrikant: {niveau}\nProfiel: {profiel}\nConstructie: {constructie}\nSpecs: {specs_tekst(cur, sid)}\n")
    extra = inbox_voor(sl, naam)
    if extra: vraag += f"\nAanvullende informatie van onze redactie (meenemen, ook eigen testervaringen):\n{extra}\n"
    r = client.messages.create(model=MODEL, max_tokens=4000, system=INSTRUCTIE,
        tools=[{"type": WEBSEARCH, "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": vraag}])
    tekst = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", tekst, re.S)
    if not m: raise ValueError("geen JSON in antwoord")
    d = json.loads(m.group(0))
    for k in ("kort", "verhaal", "goed", "minder", "voorwie", "bronnen"):
        if k not in d: raise ValueError(f"veld {k} ontbreekt")
    blob = json.dumps(d, ensure_ascii=False)
    if re.search(r"https?://|www\.", blob): raise ValueError("bevat links")
    d.update(status="concept", seizoen=seizoen, geschreven=datetime.date.today().isoformat(), door="auto")
    if "Specificaties fabrikant" not in d["bronnen"]: d["bronnen"].append("Specificaties fabrikant")
    json.dump(d, open(os.path.join(OUT, sl + ".json"), "w"), ensure_ascii=False, indent=1)
    return sl

def main():
    a = argparse.ArgumentParser(); a.add_argument("--max", type=int, default=10); a.add_argument("--slug"); a.add_argument("--opnieuw", action="store_true")
    args = a.parse_args()
    import anthropic
    client = anthropic.Anthropic()
    con = psycopg2.connect(DSN); cur = con.cursor()
    cur.execute("""SELECT DISTINCT ON (m.naam, s.model) s.id, m.naam, s.model, s.seizoen, s.niveau, s.profiel, s.constructie
                   FROM ski s JOIN merk m ON m.id=s.merk_id ORDER BY m.naam, s.model, s.seizoen DESC""")
    todo = []
    for ski in cur.fetchall():
        sl = slug(ski[1], ski[2]); p = os.path.join(OUT, sl + ".json")
        if args.slug and sl != args.slug: continue
        if os.path.exists(p):
            bestaand = json.load(open(p))
            if bestaand.get("status", "goedgekeurd") == "goedgekeurd" and not args.opnieuw: continue
            if bestaand.get("seizoen") == ski[3] and not args.opnieuw: continue
        todo.append(ski)
    print(f"{len(todo)} ski's zonder actuele review; nu {min(len(todo), args.max)}")
    for ski in todo[:args.max]:
        try: print("OK", schrijf_review(client, ski, cur), flush=True)
        except Exception as e: print("FOUT", ski[1], ski[2], e, flush=True)

if __name__ == "__main__": main()
