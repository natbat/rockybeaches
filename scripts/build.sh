#!/bin/bash
rm -f data.db || true
yaml-to-sqlite data.db stations data/stations.yml --pk=id
yaml-to-sqlite data.db places data/places.yml --pk=slug
