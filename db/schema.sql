-- Spalder ski-database – basisschema
CREATE TABLE IF NOT EXISTS merk (
  id SERIAL PRIMARY KEY,
  naam TEXT UNIQUE NOT NULL,
  website TEXT
);

CREATE TABLE IF NOT EXISTS ski (
  id SERIAL PRIMARY KEY,
  merk_id INT NOT NULL REFERENCES merk(id),
  model TEXT NOT NULL,
  seizoen TEXT NOT NULL,              -- bv. '2026/27'
  categorie TEXT,                      -- piste, allmountain, freeride, freestyle, toer
  geslacht TEXT,                       -- unisex, dames, heren
  niveau TEXT,                         -- beginner, gevorderd, expert
  profiel TEXT,                        -- bv. 'rocker-camber-rocker'
  constructie TEXT,                    -- bv. 'houtkern, titanal'
  bron_url TEXT,
  bijgewerkt TIMESTAMPTZ DEFAULT now(),
  UNIQUE (merk_id, model, seizoen)
);

CREATE TABLE IF NOT EXISTS ski_lengte (
  id SERIAL PRIMARY KEY,
  ski_id INT NOT NULL REFERENCES ski(id) ON DELETE CASCADE,
  lengte_cm INT NOT NULL,
  tip_mm INT, taille_mm INT, tail_mm INT,
  radius_m NUMERIC(4,1),
  gewicht_g INT,                       -- per ski
  UNIQUE (ski_id, lengte_cm)
);

CREATE TABLE IF NOT EXISTS score (
  ski_id INT PRIMARY KEY REFERENCES ski(id) ON DELETE CASCADE,
  grip SMALLINT, wendbaarheid SMALLINT, stabiliteit SMALLINT, drijfvermogen SMALLINT,
  speelsheid SMALLINT, vergevingsgezind SMALLINT, gewicht SMALLINT,
  methode_versie TEXT,
  bijgewerkt TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aanbieding (
  id SERIAL PRIMARY KEY,
  ski_id INT REFERENCES ski(id) ON DELETE CASCADE,
  netwerk TEXT,                        -- awin, daisycon, tradetracker
  winkel TEXT, land TEXT,
  prijs NUMERIC(8,2), valuta TEXT DEFAULT 'EUR',
  op_voorraad BOOLEAN,
  deeplink TEXT,
  bijgewerkt TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS testoordeel (
  id SERIAL PRIMARY KEY,
  ski_id INT REFERENCES ski(id) ON DELETE CASCADE,
  bron TEXT, url TEXT,
  samenvatting TEXT                    -- eigen woorden, geen overname
);
