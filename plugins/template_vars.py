from astral import LocationInfo, sun
from datasette import hookimpl
import datetime
import json
import pytz

TIDE_TIMES_SQL = """
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

BEST_TIMES_SQL = """
with lowest_tide_per_day as (
  select
    station_id,
    date(datetime) as date,
    time(datetime) as lowest_tide_time,
    min(mllw_feet) as lowest_tide
  from
    tide_predictions
  where
    station_id = (
      select
        station_id
      from
        places
      where
        slug = :place_slug
    )
  group by
    date(datetime)
)
select
  lowest_tide_per_day.date,
  lowest_tide_per_day.lowest_tide_time,
  lowest_tide_per_day.lowest_tide,
  sunrise_sunset.sunrise,
  sunrise_sunset.sunset
from
  lowest_tide_per_day
  join sunrise_sunset on sunrise_sunset.place = :place_slug
  and sunrise_sunset.day = lowest_tide_per_day.date
where
  lowest_tide_per_day.lowest_tide_time > sunrise_sunset.sunrise
  and lowest_tide_per_day.lowest_tide_time < sunrise_sunset.sunset
  and date >= date('now')
order by
  date
"""


@hookimpl
def extra_template_vars(datasette):
    async def best_times_for_place(place_slug):
        db = datasette.get_database()
        best_times = await db.execute(BEST_TIMES_SQL, {"place_slug": place_slug,})
        rows = [dict(r) for r in best_times]
        for row in rows:
            row["date"] = datetime.datetime.strptime(row["date"], "%Y-%m-%d").date()
        return rows

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
                "select * from stations where id = :station_id",
                {"station_id": place["station_id"]},
            )
        ).first()
        station_id = station["id"]
        results = await db.execute(
            TIDE_TIMES_SQL,
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
            "lowest_tide": list(sorted(heights[1:-1], key=lambda t: t["feet"]))[0],
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
        "best_times_for_place": best_times_for_place,
        "tide_data_for_place": tide_data_for_place,
        "next_30_days": next_30_days,
        "ordinal": ordinal,
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
            current = tide_times[i]
            offset_to_change = 1
            while current["feet"] == tide_times[i + offset_to_change]["feet"]:
                offset_to_change += 1
            next_ = tide_times[i + offset_to_change]
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


def ordinal(n):
    n = abs(n)
    if n > 100:
        # Normalize it to range 0-100
        n -= 100 * (n // 100)
    if 10 < n < 20:
        return "th"
    else:
        mod_10 = n % 10
        return {1: "st", 2: "nd", 3: "rd"}.get(mod_10, "th")
