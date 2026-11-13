#!/bin/bash
# Haalt de laatste code op, herberekent scores en bouwt de testsite opnieuw.
set -e
cd /opt/skidata/app && git pull -q
/opt/skidata/venv/bin/python model/scores.py
/opt/skidata/venv/bin/python site/build.py /var/www/skitest
