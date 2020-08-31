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

# Best days are the four days out of the next 30 with the lowest
# tides during daylight hours
# https://github.com/natbat/rockybeaches/issues/55
BEST_DAYS_SQL = """
with daylight_tides as (
  select
    tide_predictions.datetime,
    time(tide_predictions.datetime),
    tide_predictions.mllw_feet,
    sunrise_sunset.sunrise,
    sunrise_sunset.sunset
  from
    tide_predictions
    join sunrise_sunset on sunrise_sunset.place = :place_slug
    and sunrise_sunset.day = date(tide_predictions.datetime)
  where
    time(tide_predictions.datetime) >= sunrise
    and time(tide_predictions.datetime) <= sunset
    and tide_predictions.station_id = (
      select
        station_id
      from
        places
      where
        slug = :place_slug
    )
),
lowest_daylight_tide_per_day as (
  select
    date(datetime) as date,
    min(mllw_feet) as lowest_daylight_tide,
    time(datetime) as time,
    sunrise,
    sunset
  from
    daylight_tides
  group by
    date(datetime)
  having
    mllw_feet = min(mllw_feet)
),
best_four_days as (
  select
    *
  from
    lowest_daylight_tide_per_day
  order by
    lowest_daylight_tide
  limit
    4
)
select
  *
from
  best_four_days
order by
  date
"""


@hookimpl
def extra_template_vars(datasette):
    async def best_times_for_place(place_slug):
        db = datasette.get_database()
        best_times = await db.execute(
            BEST_DAYS_SQL,
            {
                "place_slug": place_slug,
            },
        )
        rows = [dict(r) for r in best_times]
        for row in rows:
            row["date"] = datetime.datetime.strptime(row["date"], "%Y-%m-%d").date()
        return {
            "best_details": rows,
            "best_dates": [r["date"] for r in rows],
        }

    async def tide_data_for_place(place_slug, day=None):
        db = datasette.get_database()
        place = (
            await db.execute(
                "select * from places where slug = :place_slug",
                {"place_slug": place_slug},
            )
        ).first()
        # Use the timezone to figure out today
        if day is None:
            day = datetime.datetime.now(pytz.timezone(place["time_zone"])).date()
        station_id = place["station_id"]
        results = await db.execute(
            TIDE_TIMES_SQL,
            {
                "station_id": station_id,
                "day": day.isoformat(),
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
        if len(heights) < 3:
            return None
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
        # Calculate SVG points, refs https://github.com/natbat/rockybeaches/issues/31
        min_feet = min(h["feet"] for h in heights[1:-1])
        max_feet = max(h["feet"] for h in heights[1:-1])
        feet_delta = max_feet - min_feet
        svg_points = []
        for i, height in enumerate(heights[1:-1]):
            ratio = (height["feet"] - min_feet) / feet_delta
            line_height_pct = 100 - (ratio * 100)
            svg_points.append((i, line_height_pct))
        # Figure out the lowest minima that's during daylight
        sunrise = (
            astral_info["sunrise"].astimezone(tz).time().isoformat(timespec="minutes")
        )
        sunset = (
            astral_info["sunset"].astimezone(tz).time().isoformat(timespec="minutes")
        )
        daytime_minimas = [m for m in minimas if sunrise <= m["time"] <= sunset]
        if daytime_minimas:
            lowest_daylight_minima = sorted(daytime_minimas, key=lambda m: m["feet"])[0]
        else:
            lowest_daylight_minima = None
        info = {
            "minimas": minimas,
            "maximas": maximas,
            "lowest_daylight_minima": lowest_daylight_minima,
            "heights": heights[1:-1],
            "lowest_tide": list(sorted(heights[1:-1], key=lambda t: t["feet"]))[0],
            "svg_points": " ".join("{},{:.2f}".format(i, pct) for i, pct in svg_points),
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
        "best_times_for_place": best_times_for_place,
        "tide_data_for_place": tide_data_for_place,
        "next_30_days": next_30_days,
        "ordinal": ordinal,
        "calculate_depth_view": calculate_depth_view,
        "nice_time": nice_time,
        "json": json,
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


def nice_time(s):
    # Input: 07:42:00 - Output: 2:15pm
    time = datetime.time(*map(int, s.split(":")))
    return time.strftime("%-I:%M%p").lower()


def calculate_depth_view(min_tide, max_tide, today_lowest_tide):
    today_lowest_tide = max(min_tide, today_lowest_tide)
    today_lowest_tide = min(max_tide, today_lowest_tide)
    total_width = max_tide - min_tide
    distance_from_edge = today_lowest_tide - min_tide
    left = distance_from_edge / total_width * 100
    if left > 50:
        width = left - 50
        left = 50
    else:
        width = 50 - left
    return {
        "left": left,
        "width": width,
    }
