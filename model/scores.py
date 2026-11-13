"""Scoremodel v0.1 (concept) – berekent 7 assen (1-10) uit specs.
Openbaar en uitlegbaar: elke as is een eenvoudige formule op taille, radius, constructie, profiel, niveau en gewicht.
Referentielengte: middelste beschikbare lengte."""
import os, psycopg2
DSN = os.environ.get("SKIDATA_DSN", "dbname=skidata user=skidata password=skidata_local host=localhost")
VERSIE = "0.1-concept"

def klem(x): return max(1, min(10, round(x)))

def bereken(s, l, gewicht_any):
    w = l["taille"] or 95; r = float(l["radius"] or 17)
    c = (s["constructie"] or "").lower(); p = (s["profiel"] or "").lower(); n = (s["niveau"] or "").lower()
    tail = (s["tail_type"] or "").lower()
    metaal = "metal" in c or "titanal" in c
    carbon = "carbon" in c
    rocker = p.count("rocker"); camber = "camber" in p
    twin = "twin" in tail
    expert = "expert" in n; beginner = "beginner" in n or "intermediate" in n and "advanced" not in n
    g = gewicht_any
    return dict(
        grip=klem(5 + 2*metaal + 1*camber - (w-85)/8 - 0.5*rocker + 0.5*expert),
        wendbaarheid=klem(9 - (r-13)/2 - 1*metaal + 0.5*rocker - (w-90)/15),
        stabiliteit=klem(4 + 3*metaal + (r-15)/3 + 1*expert - 1*beginner + (((g or 1800)-1800)/300)),
        drijfvermogen=klem((w-78)/3.2 + 0.7*rocker),
        speelsheid=klem(4 + 2*twin + 2*(not metaal) + 0.7*rocker - 1*expert),
        vergevingsgezind=klem(5 + 2.5*beginner + 1.5*(not metaal) + 0.5*rocker - 2*expert),
        gewicht=klem(10 - (((g or (2000 if metaal else 1800)) - 1300)/170) + 0.5*carbon),
    )

def main():
    con = psycopg2.connect(DSN); cur = con.cursor()
    cur.execute("SELECT id, constructie, profiel, niveau, tail_type FROM ski")
    for sid, c, p, n, t in cur.fetchall():
        cur.execute("SELECT lengte_cm, taille_mm, radius_m, gewicht_g FROM ski_lengte WHERE ski_id=%s ORDER BY lengte_cm", (sid,))
        rows = cur.fetchall()
        if not rows: continue
        mid = rows[len(rows)//2]
        gew = next((x[3] for x in rows if x[3]), None)
        sc = bereken(dict(constructie=c, profiel=p, niveau=n, tail_type=t), dict(taille=mid[1], radius=mid[2]), gew)
        cur.execute("""INSERT INTO score(ski_id,grip,wendbaarheid,stabiliteit,drijfvermogen,speelsheid,vergevingsgezind,gewicht,methode_versie,bijgewerkt)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now()) ON CONFLICT (ski_id) DO UPDATE SET grip=EXCLUDED.grip,wendbaarheid=EXCLUDED.wendbaarheid,
          stabiliteit=EXCLUDED.stabiliteit,drijfvermogen=EXCLUDED.drijfvermogen,speelsheid=EXCLUDED.speelsheid,vergevingsgezind=EXCLUDED.vergevingsgezind,
          gewicht=EXCLUDED.gewicht,methode_versie=EXCLUDED.methode_versie,bijgewerkt=now()""", (sid, *sc.values(), VERSIE))
    con.commit(); print("scores bijgewerkt")

if __name__ == "__main__": main()
