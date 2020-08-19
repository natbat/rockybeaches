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
    async def tide_data_for_station(station_id, day=None):
        db = datasette.get_database()
        results = await db.execute(
            SQL,
            {
                "station_id": station_id,
                "day": (day or datetime.date.today()).isoformat(),
            },
        )
        tide_times = list(dict(r) for r in results)
        minimas, maximas = get_minimas_maximas(tide_times)
        place = (
            await db.execute(
                "select * from places where station_id = (select id from stations where station_id = :station_id)",
                {"station_id": station_id},
            )
        ).first()
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
        }
        info.update(
            {
                key: value.astimezone(tz).time().isoformat(timespec="seconds")
                for key, value in astral_info.items()
            }
        )
        return info

    return {
        "json": json,
        "tide_data_for_station": tide_data_for_station,
    }


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
        if previous["mllw_feet"] < row["mllw_feet"] > next_["mllw_feet"]:
            maximas.append(row)
        if previous["mllw_feet"] > row["mllw_feet"] < next_["mllw_feet"]:
            minimas.append(row)
    return minimas, maximas
