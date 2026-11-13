# Elk seizoen opnieuw – werkwijze

Webadressen bevatten **geen seizoen**: `/ski-test/volkl-mantra-102/` blijft elk jaar dezelfde pagina. Zo bouwt elke pagina jaar op jaar waarde op en zijn er geen redirects nodig.

## Nieuw seizoen (vanaf september, als de nieuwe modellen online staan)
1. Productlijsten ophalen per categorie: `python scrapers/evo_lijst.py <categorie-url> <jaar> 12 > scrapers/lijsten/<categorie>-<seizoen>.txt`
2. Specs binnenhalen: `python scrapers/evo.py scrapers/lijsten/<categorie>-<seizoen>.txt <categorie>`
3. Scores herberekenen (`model/scores.py`) en pagina's bouwen (`site/build.py`) – of in één keer `./deploy.sh`.

Wat er dan automatisch gebeurt:
- Bestaande ski (zelfde merk + model) → nieuw seizoen op dezelfde pagina; vorige seizoenen blijven zichtbaar onder "Eerdere seizoenen".
- Nieuwe ski → nieuwe pagina.
- Ski die niet meer verkocht wordt → pagina blijft staan (met laatste seizoen); later link naar de opvolger.
- Hernoemde ski (bv. Sender Free 100 → Sender 100) → handmatig koppelen (alias), zodat de oude pagina de nieuwe wordt.

## Reviews
Per ski een bestand `content/reviews/<slug>.json` (kort, verhaal, goed, minder, voor wie, bronnen). Bronnen worden bij naam genoemd, nooit gelinkt, in eigen woorden samengevat. Bij een nieuw seizoen: kijken of de ski veranderd is en of er nieuwe tests zijn.
