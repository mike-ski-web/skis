"""Haalt Daisycon-productfeeds op en koppelt producten aan ski's in de database (tabel aanbieding).
Match: titel zonder merk moet beginnen met de modelnaam; '+ binding' en kleur-/editievarianten worden genoteerd.
Gebruik: python feeds/daisycon.py"""
import os, re, csv, json, io, unicodedata, urllib.request, psycopg2
csv.field_size_limit(10**8)
HIER = os.path.dirname(os.path.abspath(__file__))
DSN = os.environ.get("SKIDATA_DSN", "dbname=skidata user=skidata password=skidata_local host=localhost")
CFG = json.load(open(os.path.join(HIER, "bronnen.json")))["daisycon"]
MEDIA = os.environ.get(CFG["media_id_env"], "201595")
UIT = re.compile(r"\b(jr|junior|kids|boot|schoen|helm|bril|stok|pole|binding only|skin|tas|bag|t-shirt|hawx|grip pad)\b")
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()
def main():
    con = psycopg2.connect(DSN); cur = con.cursor()
    cur.execute("SELECT DISTINCT ON (m.naam,s.model) s.id, m.naam, s.model, s.geslacht FROM ski s JOIN merk m ON m.id=s.merk_id ORDER BY m.naam,s.model,s.seizoen DESC")
    ski = [(sid, norm(merk), norm(model), g) for sid, merk, model, g in cur.fetchall()]
    ski.sort(key=lambda x: -len(x[2]))  # langste modelnaam eerst (ARV 88 voor ARV 8)
    cur.execute("DELETE FROM aanbieding WHERE netwerk='daisycon'")
    totaal = 0
    for f in CFG["feeds"]:
        url = (f"https://daisycon.io/datafeed/?media_id={MEDIA}&standard_id={f['standard_id']}&language_code=nl&locale_id=1"
               f"&type=csv&program_id={f['program_id']}&html_transform=none&rawdata=false&encoding=utf8&general=false")
        data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.5 skidata"}), timeout=180).read().decode("utf8", "ignore")
        beste = {}
        for r in csv.DictReader(io.StringIO(data), delimiter=";"):
            merk = norm(r.get("brand", "")); titel = norm(r.get("title", ""))
            if not merk or UIT.search(titel): continue
            rest = titel[len(merk):].strip() if titel.startswith(merk) else titel
            for sid, m, model, g in ski:
                if m != merk and not (m == "volkl" and merk == "volkl"): continue
                if rest == model or rest.startswith(model + " "):
                    extra = rest[len(model):].strip()
                    if re.match(r"^(w|women|dames)\b", extra) and g != "dames": continue
                    if g == "dames" and not re.search(r"\b(w|women|dames)\b", model + " " + extra) and model.endswith(" w") is False: pass
                    try: prijs = float(r.get("price") or 0)
                    except ValueError: continue
                    key = (sid, "binding" in extra)
                    voorraad = str(r.get("in_stock", "")).lower() in ("true", "1", "yes", "ja")
                    oud = beste.get(key)
                    if not oud or (voorraad and not oud[1]) or (voorraad == oud[1] and prijs < oud[0]):
                        beste[key] = (prijs, voorraad, r.get("link"), r.get("title"), r.get("image_default") or r.get("image_large"))
                    break
        for (sid, met_binding), (prijs, voorraad, link, titel, img) in beste.items():
            cur.execute("INSERT INTO aanbieding(ski_id,netwerk,winkel,land,prijs,op_voorraad,deeplink,bijgewerkt) VALUES (%s,'daisycon',%s,%s,%s,%s,%s,now())",
                        (sid, f["winkel"] + (" (incl. binding)" if met_binding else ""), f["land"], prijs, voorraad, link))
            totaal += 1
        print(f["winkel"], ":", len(beste), "koppelingen")
    con.commit(); print("totaal", totaal)
if __name__ == "__main__": main()
