from astral import LocationInfo, sun
from datasette import hookimpl
import datetime
import json
import pytz

SQL = """
with previous_day_last_record as (
  select
    station_id,
    datetime,
    mllw_feet
  from
    tide_predictions
  where
    date("datetime") = date(:day, '-1 days')
    and "station_id" = :station_id
  order by
    datetime desc
  limit
    1
), next_day_first_record as (
  select
    station_id,
    datetime,
    mllw_feet
  from
    tide_predictions
  where
    date("datetime") = date(:day, '1 days')
    and "station_id" = :station_id
  order by
    datetime
  limit
    1
)
select * from previous_day_last_record
  union
select * from next_day_first_record
  union
select
  station_id,
  datetime,
  mllw_feet
from
  tide_predictions
where
  date("datetime") = :day
  and "station_id" = :station_id
order by
  station_id,
  datetime
"""


@hookimpl
def extra_template_vars(datasette):
    async def tide_data_for_place(place_slug, day=None):
        db = datasette.get_database()
        place = (
            await db.execute(
                "select * from places where slug = :place_slug",
                {"place_slug": place_slug},
            )
        ).first()
        station = (
            await db.execute(
                "select * from stations where id = :station_db_id",
                {"station_db_id": place["station_id"]},
            )
        ).first()
        station_id = station["station_id"]
        results = await db.execute(
            SQL,
            {
                "station_id": station_id,
                "day": (day or datetime.date.today()).isoformat(),
            },
        )
        tide_times = list(dict(r) for r in results)
        heights = [
            {
                "time": tide_time["datetime"].split()[-1],
                "time_pct": round(
                    100 * time_to_float(tide_time["datetime"].split()[-1]), 2
                ),
                "feet": tide_time["mllw_feet"],
            }
            for tide_time in tide_times
        ]
        minimas, maximas = get_minimas_maximas(heights)
        location_info = LocationInfo(
            place["address"],
            "",
            place["time_zone"],
            place["latitude"],
            place["longitude"],
        )
        tz = pytz.timezone(place["time_zone"])
        astral_info = sun.sun(location_info.observer, date=day)
        info = {
            "minimas": minimas,
            "maximas": maximas,
            "heights": heights[1:-1],
        }
        info.update(
            {
                key: value.astimezone(tz).time().isoformat(timespec="seconds")
                for key, value in astral_info.items()
            }
        )
        info.update(
            {
                "{}_pct".format(key): round(
                    100
                    * time_to_float(
                        value.astimezone(tz).time().isoformat(timespec="seconds")
                    ),
                    2,
                )
                for key, value in astral_info.items()
            }
        )
        return info

    return {
        "json": json,
        "tide_data_for_place": tide_data_for_place,
        "next_30_days": next_30_days,
    }


def next_30_days():
    today = datetime.date.today()
    for i in range(0, 30):
        yield today + datetime.timedelta(days=i)


def get_minimas_maximas(tide_times):
    minimas = []
    maximas = []
    for i, row in enumerate(tide_times):
        try:
            previous = tide_times[i - 1]
        except IndexError:
            continue
        try:
            next_ = tide_times[i + 1]
        except IndexError:
            continue
        if previous["feet"] < row["feet"] > next_["feet"]:
            maximas.append(row)
        if previous["feet"] > row["feet"] < next_["feet"]:
            minimas.append(row)
    return minimas, maximas


def time_to_float(s):
    if s.count(":") == 2:
        hh, mm, ss = map(float, s.split(":"))
    else:
        hh, mm = map(float, s.split(":"))
        ss = 0.0
    # 1 hour = 1/24th, 1 minute = 60th/hour, 1 second = 60th/minute
    return hh / 24 + ((mm / 60) * (1 / 24)) + ((ss / 60) * (1 / 24 / 60))
