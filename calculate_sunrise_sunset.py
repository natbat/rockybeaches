from astral import LocationInfo, sun
import datetime
import httpx
import pytz
import sqlite_utils
import sys
from urllib.parse import urlencode


def calculate_sunrise_sunset(place):
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    end_date = yesterday + datetime.timedelta(days=32)
    location_info = LocationInfo(
        place["address"], "", place["time_zone"], place["latitude"], place["longitude"]
    )
    day = yesterday
    day_infos = []
    tz = pytz.timezone(place["time_zone"])
    while day <= end_date:
        info = sun.sun(location_info.observer, date=day)
        day_info = {
            "place": place["slug"],
            "day": day.isoformat(),
        }
        day_info.update(
            {
                key: value.astimezone(tz).time().isoformat(timespec="seconds")
                for key, value in info.items()
            }
        )
        day_infos.append(day_info)
        day += datetime.timedelta(days=1)
    return day_infos


if __name__ == "__main__":
    assert sys.argv[-1].endswith(".db")
    db = sqlite_utils.Database(sys.argv[-1])
    table = db.table(
        "sunrise_sunset",
        pk=("place", "day"),
        foreign_keys=(("place", "places", "slug"),),
    )
    for place in db["places"].rows_where("live_on_site = 1"):
        table.insert_all(calculate_sunrise_sunset(place), replace=True)
