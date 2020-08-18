import httpx
import sqlite_utils
import sys
from urllib.parse import urlencode


def fetch_species_counts(place):
    url = "https://api.inaturalist.org/v1/observations/species_counts?" + urlencode(
        {
            "quality_grade": "research",
            "lat": place["latitude"],
            "lng": place["longitude"],
            "radius": place["radius_km"],
        }
    )
    return httpx.get(url).json()["results"]


if __name__ == "__main__":
    assert sys.argv[-1].endswith(".db")
    db = sqlite_utils.Database(sys.argv[-1])
    for place in db["places"].rows:
        for species_count in fetch_species_counts(place):
            db["taxons"].insert(
                species_count["taxon"], pk="id", replace=True, alter=True
            )
            db["species_counts"].insert(
                {
                    "place": place["slug"],
                    "taxon": species_count["taxon"]["id"],
                    "count": species_count["count"],
                },
                pk=("place", "taxon"),
                foreign_keys=("taxon", "place"),
                replace=True,
            )