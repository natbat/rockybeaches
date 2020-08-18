#!/bin/bash
rm -f data.db || true
yaml-to-sqlite data.db stations data/stations.yml --pk=id
yaml-to-sqlite data.db places data/places.yml --pk=slug
python fetch_noaa_tide_times.py data.db
python calculate_sunrise_sunset.py data.db
python fetch_inaturalist.py data.db
