import datetime
import httpx
import sqlite_utils
import sys
from urllib.parse import urlencode


def fetch_predictions(station_id):
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    end_date = yesterday + datetime.timedelta(days=32)
    response = httpx.get(
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"
        + urlencode(
            {
                "begin_date": yesterday.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d"),
                "product": "predictions",
                "station": station_id,
                "datum": "mllw",
                "time_zone": "lst_ldt",
                "units": "english",
                "format": "json",
            }
        )
    )
    return response.json()["predictions"]


def fetch_noaa_tide_times(filepath):
    db = sqlite_utils.Database(filepath)
    tide_predictions = db.table("tide_predictions", pk=("station_id", "datetime"))
    for station in db["stations"].rows:
        predictions = fetch_predictions(station["id"])
        with db.conn:
            tide_predictions.insert_all(
                (
                    {
                        "station_id": station["id"],
                        "datetime": p["t"],
                        "mllw_feet": float(p["v"]),
                    }
                    for p in predictions
                ),
                replace=True,
            )


if __name__ == "__main__":
    assert sys.argv[-1].endswith(".db")
    fetch_noaa_tide_times(sys.argv[-1])
