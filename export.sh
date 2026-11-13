#!/bin/bash
# Maakt een publiceerbare versie van /ski-test/: zonder testbalk en zonder noindex.
# Resultaat: /opt/skidata/export/ski-test-<datum>.zip  → uitpakken in de webroot van de site.
set -e
cd /opt/skidata/app
OUT=/tmp/export-ski-test; rm -rf $OUT
SKIDATA_LIVE=1 /opt/skidata/venv/bin/python site/build.py $OUT
mkdir -p /opt/skidata/export; Z=/opt/skidata/export/ski-test-$(date +%Y%m%d).zip
(cd $OUT && zip -qr $Z ski-test); rm -rf $OUT; echo $Z
