# Skis – Spalder ski-database & skifinder

Eigen ski-database met transparant scoremodel, als skifinder/vergelijker op Spalder-sites.
Pilot: **Skiinformatie.nl** (WordPress, via shortcode/blok – zelfde aanpak als de weerkaarten).

## Structuur
- `scrapers/` – per merk een scraper (Playwright) voor specs van fabrikanten-sites
- `db/` – Postgres-schema en migraties
- `api/` – kleine API (FastAPI) die de widget voedt
- `widget/` – embeddable skifinder/vergelijker (JS)

## Databronnen
Alleen openbare data: fabrikanten-sites (specs), affiliate-productfeeds (Awin, Daisycon, TradeTracker: prijs/voorraad/deeplink), externe testoordelen (eigen samenvatting + bronlink).

## Scoremodel (7 assen, 1–10)
1. Grip & carving 2. Wendbaarheid 3. Stabiliteit op snelheid 4. Drijfvermogen
5. Speelsheid 6. Vergevingsgezindheid 7. Gewicht/toerbaarheid
Berekend uit specs; formules worden gepubliceerd.

## Seizoen
Eén veld `seizoen` (bv. `2026/27`). Retail "2027" = 2026/27.

## Server
DigitalOcean droplet `skidata` (Ubuntu 24.04), code in `/opt/skidata/app`, venv in `/opt/skidata/venv`.
