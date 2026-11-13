"""Scoremodel v0.2 – zeven assen (1-10) uit specs.
Stap 1: per as een ruwe waarde uit taille, radius, constructie, profiel, niveau en gewicht.
Stap 2: schalen binnen de categorie en het seizoen (laagste ~2, hoogste ~9), zodat scores onderling vergelijkbaar zijn.
Formules staan hieronder en worden zo op de site uitgelegd."""
import os, psycopg2
DSN = os.environ.get("SKIDATA_DSN", "dbname=skidata user=skidata password=skidata_local host=localhost")
VERSIE = "0.2"
ASSEN = ["grip","wendbaarheid","stabiliteit","drijfvermogen","speelsheid","vergevingsgezind","gewicht"]

def ruw(s, w, r, g):
    c = (s["constructie"] or "").lower(); p = (s["profiel"] or "").lower(); n = (s["niveau"] or "").lower(); t = (s["tail_type"] or "").lower()
    metaal = 1 if ("metal" in c or "titanal" in c) else 0
    carbon = 1 if "carbon" in c else 0
    rocker = p.count("rocker"); camber = 1 if "camber" in p else 0
    twin = 1 if "twin" in t else 0
    expert = 1 if "expert" in n else 0
    makkelijk = 1 if "beginner" in n else 0
    g = g or (2050 if metaal else 1800) * (w / 95)
    return dict(
        grip=2*metaal + camber - w/12 - 0.4*rocker + 0.5*expert - r/20,
        wendbaarheid=-r/2.5 - metaal - w/25 + 0.4*rocker - g/1500,
        stabiliteit=2.5*metaal + r/4 + g/600 + expert - makkelijk,
        drijfvermogen=w/4 + 0.8*rocker - metaal*0.3,
        speelsheid=2*twin + 1.5*(1-metaal) + 0.5*rocker - expert - g/1500,
        vergevingsgezind=2*makkelijk + 1.5*(1-metaal) + 0.5*rocker - 1.5*expert - g/2000,
        gewicht=-g/150 + 0.5*carbon,
    )

def main():
    con = psycopg2.connect(DSN); cur = con.cursor()
    cur.execute("SELECT id, categorie, seizoen, constructie, profiel, niveau, tail_type FROM ski")
    alles = {}
    for sid, cat, sz, c, p, n, t in cur.fetchall():
        cur.execute("SELECT lengte_cm, taille_mm, radius_m, gewicht_g FROM ski_lengte WHERE ski_id=%s ORDER BY lengte_cm", (sid,))
        rows = cur.fetchall()
        if not rows: continue
        mid = rows[len(rows)//2]
        gew = next((x[3] for x in rows if x[3]), None)
        alles[sid] = ((cat, sz), ruw(dict(constructie=c, profiel=p, niveau=n, tail_type=t), mid[1] or 95, float(mid[2] or 17), gew))
    groepen = {}
    for sid, (k, v) in alles.items(): groepen.setdefault(k, []).append((sid, v))
    for k, lijst in groepen.items():
        sc = {sid: {} for sid, _ in lijst}
        for a in ASSEN:
            waarden = sorted(v[a] for _, v in lijst)
            for sid, v in lijst:
                rang = sum(1 for x in waarden if x < v[a]) + 0.5 * (sum(1 for x in waarden if x == v[a]) - 1)
                pct = rang / max(1, len(waarden) - 1)
                sc[sid][a] = max(1, min(10, round(2 + 7 * pct)))
        for sid, s in sc.items():
            cur.execute("""INSERT INTO score(ski_id,grip,wendbaarheid,stabiliteit,drijfvermogen,speelsheid,vergevingsgezind,gewicht,methode_versie,bijgewerkt)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now()) ON CONFLICT (ski_id) DO UPDATE SET grip=EXCLUDED.grip,wendbaarheid=EXCLUDED.wendbaarheid,
              stabiliteit=EXCLUDED.stabiliteit,drijfvermogen=EXCLUDED.drijfvermogen,speelsheid=EXCLUDED.speelsheid,vergevingsgezind=EXCLUDED.vergevingsgezind,
              gewicht=EXCLUDED.gewicht,methode_versie=EXCLUDED.methode_versie,bijgewerkt=now()""", (sid, *[s[a] for a in ASSEN], VERSIE))
    con.commit(); print("scores v%s bijgewerkt voor %d ski's" % (VERSIE, len(alles)))

if __name__ == "__main__": main()
