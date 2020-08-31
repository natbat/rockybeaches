from datasette.app import Datasette
from yaml_to_sqlite.cli import cli as yaml_to_sqlite_cli
from plugins.template_vars import (
    extra_template_vars,
    get_minimas_maximas,
    calculate_depth_view,
)
import httpx
import datetime
import pytest
import pathlib
import sqlite_utils

root = pathlib.Path(__file__).parent.resolve()


@pytest.fixture
def db_path(tmpdir):
    db_path = str(tmpdir / "data.db")
    yaml_to_sqlite_cli.callback(
        db_path, "places", open(root / "airtable" / "tidepool_areas.yml"), "slug"
    )
    db = sqlite_utils.Database(db_path)
    # Fake tide data
    station_ids = {p["station_id"] for p in db["places"].rows if p["station_id"]}
    for station_id in station_ids:
        db["tide_predictions"].insert_all(
            generate_tide_data(station_id), pk=("station_id", "datetime")
        )
    return db_path


@pytest.fixture
def ds(db_path):
    return Datasette([db_path], plugins_dir=str(root / "plugins"))


@pytest.mark.asyncio
async def test_live_pages(ds):
    # Live pages should all 200, not 500
    async with httpx.AsyncClient(app=ds.app()) as client:
        response = await client.get(
            "http://localhost/data/places.json?live_on_site=1&_shape=array"
        )
        slugs = [p["slug"] for p in response.json()]
        for slug in slugs:
            response = await client.get("http://localhost/us/{}".format(slug))
            assert response.status_code == 200, slug


@pytest.mark.asyncio
async def test_tide_data_for_place(ds):
    tide_data_for_place = extra_template_vars(ds)["tide_data_for_place"]
    tide_data = await tide_data_for_place("pillar-point", datetime.date(2020, 8, 19))
    heights = tide_data.pop("heights")
    svg_points = tide_data.pop("svg_points")
    expected = {
        "minimas": [
            {"time": "05:42", "time_pct": 23.75, "feet": -0.77},
            {"time": "17:30", "time_pct": 72.92, "feet": 1.979},
        ],
        "maximas": [
            {"time": "12:12", "time_pct": 50.83, "feet": 4.97},
            {"time": "23:24", "time_pct": 97.5, "feet": 6.397},
        ],
        "lowest_tide": {"time": "05:42", "time_pct": 23.75, "feet": -0.77},
        "lowest_daylight_minima": {"feet": 1.979, "time": "17:30", "time_pct": 72.92},
        "dawn": "06:02:08",
        "sunrise": "06:30:10",
        "noon": "13:13:37",
        "sunset": "19:56:05",
        "dusk": "20:24:02",
        "dawn_pct": 25.15,
        "sunrise_pct": 27.09,
        "noon_pct": 55.11,
        "sunset_pct": 83.06,
        "dusk_pct": 85.0,
    }
    assert tide_data == expected
    assert len(heights) == 240
    # This one has a nice round-ish number for time_pct
    assert heights[-12] == {
        "feet": 6.253,
        "time": "22:48",
        "time_pct": 95.0,
    }
    assert svg_points.startswith("0,6.7")
    assert len(svg_points.split()) == 240


@pytest.mark.asyncio
async def test_tide_data_for_place_if_day_not_available(ds):
    tide_data_for_place = extra_template_vars(ds)["tide_data_for_place"]
    tide_data = await tide_data_for_place("pillar-point", datetime.date(2020, 8, 25))
    assert tide_data is None


@pytest.mark.parametrize(
    "input,expected_minimas,expected_maximas",
    [
        # Just one minima
        ([0.5, 0.4, 0.5], [0.4], []),
        # Two minimas, one maxima
        ([0.5, 0.4, 0.5, 0.3, 0.5], [0.4, 0.3], [0.5]),
        # Confusing case: duplicate values at minima
        ([0.5, 0.4, 0.4, 0.5, 0.3, 0.5], [0.4, 0.3], [0.5]),
    ],
)
def test_get_minimas_maximas(input, expected_minimas, expected_maximas):
    input_reformatted = [{"feet": f} for f in input]
    expected_minimas_reformatted = [{"feet": f} for f in expected_minimas]
    expected_maximas_reformatted = [{"feet": f} for f in expected_maximas]
    minimas, maximas = get_minimas_maximas(input_reformatted)
    assert minimas == expected_minimas_reformatted
    assert maximas == expected_maximas_reformatted


@pytest.mark.parametrize(
    "min_tide,max_tide,today_lowest_tide,expected_left,expected_width",
    [
        (0, 10, 3, 30, 20),
        (0, 10, 7, 50, 20),
        # Capped at min/max values
        (0, 10, -1, 0, 50),
        (0, 10, 11, 50, 50),
    ],
)
def test_calculate_depth_view(
    min_tide, max_tide, today_lowest_tide, expected_left, expected_width
):
    actual = calculate_depth_view(min_tide, max_tide, today_lowest_tide)
    assert actual == {
        "left": expected_left,
        "width": expected_width,
    }


def generate_tide_data(station_id):
    return [
        {"station_id": station_id, "datetime": "2020-08-18 23:54", "mllw_feet": 5.999},
        {"station_id": station_id, "datetime": "2020-08-19 00:00", "mllw_feet": 5.913},
        {"station_id": station_id, "datetime": "2020-08-19 00:06", "mllw_feet": 5.822},
        {"station_id": station_id, "datetime": "2020-08-19 00:12", "mllw_feet": 5.726},
        {"station_id": station_id, "datetime": "2020-08-19 00:18", "mllw_feet": 5.623},
        {"station_id": station_id, "datetime": "2020-08-19 00:24", "mllw_feet": 5.516},
        {"station_id": station_id, "datetime": "2020-08-19 00:30", "mllw_feet": 5.403},
        {"station_id": station_id, "datetime": "2020-08-19 00:36", "mllw_feet": 5.285},
        {"station_id": station_id, "datetime": "2020-08-19 00:42", "mllw_feet": 5.163},
        {"station_id": station_id, "datetime": "2020-08-19 00:48", "mllw_feet": 5.036},
        {"station_id": station_id, "datetime": "2020-08-19 00:54", "mllw_feet": 4.905},
        {"station_id": station_id, "datetime": "2020-08-19 01:00", "mllw_feet": 4.77},
        {"station_id": station_id, "datetime": "2020-08-19 01:06", "mllw_feet": 4.631},
        {"station_id": station_id, "datetime": "2020-08-19 01:12", "mllw_feet": 4.489},
        {"station_id": station_id, "datetime": "2020-08-19 01:18", "mllw_feet": 4.343},
        {"station_id": station_id, "datetime": "2020-08-19 01:24", "mllw_feet": 4.194},
        {"station_id": station_id, "datetime": "2020-08-19 01:30", "mllw_feet": 4.042},
        {"station_id": station_id, "datetime": "2020-08-19 01:36", "mllw_feet": 3.887},
        {"station_id": station_id, "datetime": "2020-08-19 01:42", "mllw_feet": 3.73},
        {"station_id": station_id, "datetime": "2020-08-19 01:48", "mllw_feet": 3.571},
        {"station_id": station_id, "datetime": "2020-08-19 01:54", "mllw_feet": 3.41},
        {"station_id": station_id, "datetime": "2020-08-19 02:00", "mllw_feet": 3.248},
        {"station_id": station_id, "datetime": "2020-08-19 02:06", "mllw_feet": 3.084},
        {"station_id": station_id, "datetime": "2020-08-19 02:12", "mllw_feet": 2.92},
        {"station_id": station_id, "datetime": "2020-08-19 02:18", "mllw_feet": 2.755},
        {"station_id": station_id, "datetime": "2020-08-19 02:24", "mllw_feet": 2.59},
        {"station_id": station_id, "datetime": "2020-08-19 02:30", "mllw_feet": 2.426},
        {"station_id": station_id, "datetime": "2020-08-19 02:36", "mllw_feet": 2.262},
        {"station_id": station_id, "datetime": "2020-08-19 02:42", "mllw_feet": 2.099},
        {"station_id": station_id, "datetime": "2020-08-19 02:48", "mllw_feet": 1.937},
        {"station_id": station_id, "datetime": "2020-08-19 02:54", "mllw_feet": 1.777},
        {"station_id": station_id, "datetime": "2020-08-19 03:00", "mllw_feet": 1.619},
        {"station_id": station_id, "datetime": "2020-08-19 03:06", "mllw_feet": 1.464},
        {"station_id": station_id, "datetime": "2020-08-19 03:12", "mllw_feet": 1.312},
        {"station_id": station_id, "datetime": "2020-08-19 03:18", "mllw_feet": 1.163},
        {"station_id": station_id, "datetime": "2020-08-19 03:24", "mllw_feet": 1.017},
        {"station_id": station_id, "datetime": "2020-08-19 03:30", "mllw_feet": 0.876},
        {"station_id": station_id, "datetime": "2020-08-19 03:36", "mllw_feet": 0.739},
        {"station_id": station_id, "datetime": "2020-08-19 03:42", "mllw_feet": 0.606},
        {"station_id": station_id, "datetime": "2020-08-19 03:48", "mllw_feet": 0.478},
        {"station_id": station_id, "datetime": "2020-08-19 03:54", "mllw_feet": 0.356},
        {"station_id": station_id, "datetime": "2020-08-19 04:00", "mllw_feet": 0.239},
        {"station_id": station_id, "datetime": "2020-08-19 04:06", "mllw_feet": 0.127},
        {"station_id": station_id, "datetime": "2020-08-19 04:12", "mllw_feet": 0.022},
        {"station_id": station_id, "datetime": "2020-08-19 04:18", "mllw_feet": -0.078},
        {"station_id": station_id, "datetime": "2020-08-19 04:24", "mllw_feet": -0.171},
        {"station_id": station_id, "datetime": "2020-08-19 04:30", "mllw_feet": -0.258},
        {"station_id": station_id, "datetime": "2020-08-19 04:36", "mllw_feet": -0.338},
        {"station_id": station_id, "datetime": "2020-08-19 04:42", "mllw_feet": -0.412},
        {"station_id": station_id, "datetime": "2020-08-19 04:48", "mllw_feet": -0.479},
        {"station_id": station_id, "datetime": "2020-08-19 04:54", "mllw_feet": -0.539},
        {"station_id": station_id, "datetime": "2020-08-19 05:00", "mllw_feet": -0.592},
        {"station_id": station_id, "datetime": "2020-08-19 05:06", "mllw_feet": -0.639},
        {"station_id": station_id, "datetime": "2020-08-19 05:12", "mllw_feet": -0.678},
        {"station_id": station_id, "datetime": "2020-08-19 05:18", "mllw_feet": -0.711},
        {"station_id": station_id, "datetime": "2020-08-19 05:24", "mllw_feet": -0.736},
        {"station_id": station_id, "datetime": "2020-08-19 05:30", "mllw_feet": -0.755},
        {"station_id": station_id, "datetime": "2020-08-19 05:36", "mllw_feet": -0.766},
        {"station_id": station_id, "datetime": "2020-08-19 05:42", "mllw_feet": -0.77},
        {"station_id": station_id, "datetime": "2020-08-19 05:48", "mllw_feet": -0.767},
        {"station_id": station_id, "datetime": "2020-08-19 05:54", "mllw_feet": -0.758},
        {"station_id": station_id, "datetime": "2020-08-19 06:00", "mllw_feet": -0.741},
        {"station_id": station_id, "datetime": "2020-08-19 06:06", "mllw_feet": -0.717},
        {"station_id": station_id, "datetime": "2020-08-19 06:12", "mllw_feet": -0.687},
        {"station_id": station_id, "datetime": "2020-08-19 06:18", "mllw_feet": -0.649},
        {"station_id": station_id, "datetime": "2020-08-19 06:24", "mllw_feet": -0.605},
        {"station_id": station_id, "datetime": "2020-08-19 06:30", "mllw_feet": -0.554},
        {"station_id": station_id, "datetime": "2020-08-19 06:36", "mllw_feet": -0.497},
        {"station_id": station_id, "datetime": "2020-08-19 06:42", "mllw_feet": -0.433},
        {"station_id": station_id, "datetime": "2020-08-19 06:48", "mllw_feet": -0.363},
        {"station_id": station_id, "datetime": "2020-08-19 06:54", "mllw_feet": -0.287},
        {"station_id": station_id, "datetime": "2020-08-19 07:00", "mllw_feet": -0.205},
        {"station_id": station_id, "datetime": "2020-08-19 07:06", "mllw_feet": -0.117},
        {"station_id": station_id, "datetime": "2020-08-19 07:12", "mllw_feet": -0.023},
        {"station_id": station_id, "datetime": "2020-08-19 07:18", "mllw_feet": 0.075},
        {"station_id": station_id, "datetime": "2020-08-19 07:24", "mllw_feet": 0.179},
        {"station_id": station_id, "datetime": "2020-08-19 07:30", "mllw_feet": 0.287},
        {"station_id": station_id, "datetime": "2020-08-19 07:36", "mllw_feet": 0.4},
        {"station_id": station_id, "datetime": "2020-08-19 07:42", "mllw_feet": 0.518},
        {"station_id": station_id, "datetime": "2020-08-19 07:48", "mllw_feet": 0.639},
        {"station_id": station_id, "datetime": "2020-08-19 07:54", "mllw_feet": 0.763},
        {"station_id": station_id, "datetime": "2020-08-19 08:00", "mllw_feet": 0.891},
        {"station_id": station_id, "datetime": "2020-08-19 08:06", "mllw_feet": 1.022},
        {"station_id": station_id, "datetime": "2020-08-19 08:12", "mllw_feet": 1.155},
        {"station_id": station_id, "datetime": "2020-08-19 08:18", "mllw_feet": 1.291},
        {"station_id": station_id, "datetime": "2020-08-19 08:24", "mllw_feet": 1.428},
        {"station_id": station_id, "datetime": "2020-08-19 08:30", "mllw_feet": 1.567},
        {"station_id": station_id, "datetime": "2020-08-19 08:36", "mllw_feet": 1.707},
        {"station_id": station_id, "datetime": "2020-08-19 08:42", "mllw_feet": 1.848},
        {"station_id": station_id, "datetime": "2020-08-19 08:48", "mllw_feet": 1.989},
        {"station_id": station_id, "datetime": "2020-08-19 08:54", "mllw_feet": 2.13},
        {"station_id": station_id, "datetime": "2020-08-19 09:00", "mllw_feet": 2.271},
        {"station_id": station_id, "datetime": "2020-08-19 09:06", "mllw_feet": 2.411},
        {"station_id": station_id, "datetime": "2020-08-19 09:12", "mllw_feet": 2.551},
        {"station_id": station_id, "datetime": "2020-08-19 09:18", "mllw_feet": 2.689},
        {"station_id": station_id, "datetime": "2020-08-19 09:24", "mllw_feet": 2.825},
        {"station_id": station_id, "datetime": "2020-08-19 09:30", "mllw_feet": 2.959},
        {"station_id": station_id, "datetime": "2020-08-19 09:36", "mllw_feet": 3.091},
        {"station_id": station_id, "datetime": "2020-08-19 09:42", "mllw_feet": 3.221},
        {"station_id": station_id, "datetime": "2020-08-19 09:48", "mllw_feet": 3.347},
        {"station_id": station_id, "datetime": "2020-08-19 09:54", "mllw_feet": 3.471},
        {"station_id": station_id, "datetime": "2020-08-19 10:00", "mllw_feet": 3.591},
        {"station_id": station_id, "datetime": "2020-08-19 10:06", "mllw_feet": 3.707},
        {"station_id": station_id, "datetime": "2020-08-19 10:12", "mllw_feet": 3.82},
        {"station_id": station_id, "datetime": "2020-08-19 10:18", "mllw_feet": 3.928},
        {"station_id": station_id, "datetime": "2020-08-19 10:24", "mllw_feet": 4.031},
        {"station_id": station_id, "datetime": "2020-08-19 10:30", "mllw_feet": 4.13},
        {"station_id": station_id, "datetime": "2020-08-19 10:36", "mllw_feet": 4.224},
        {"station_id": station_id, "datetime": "2020-08-19 10:42", "mllw_feet": 4.313},
        {"station_id": station_id, "datetime": "2020-08-19 10:48", "mllw_feet": 4.397},
        {"station_id": station_id, "datetime": "2020-08-19 10:54", "mllw_feet": 4.475},
        {"station_id": station_id, "datetime": "2020-08-19 11:00", "mllw_feet": 4.548},
        {"station_id": station_id, "datetime": "2020-08-19 11:06", "mllw_feet": 4.616},
        {"station_id": station_id, "datetime": "2020-08-19 11:12", "mllw_feet": 4.677},
        {"station_id": station_id, "datetime": "2020-08-19 11:18", "mllw_feet": 4.733},
        {"station_id": station_id, "datetime": "2020-08-19 11:24", "mllw_feet": 4.783},
        {"station_id": station_id, "datetime": "2020-08-19 11:30", "mllw_feet": 4.827},
        {"station_id": station_id, "datetime": "2020-08-19 11:36", "mllw_feet": 4.865},
        {"station_id": station_id, "datetime": "2020-08-19 11:42", "mllw_feet": 4.897},
        {"station_id": station_id, "datetime": "2020-08-19 11:48", "mllw_feet": 4.923},
        {"station_id": station_id, "datetime": "2020-08-19 11:54", "mllw_feet": 4.944},
        {"station_id": station_id, "datetime": "2020-08-19 12:00", "mllw_feet": 4.958},
        {"station_id": station_id, "datetime": "2020-08-19 12:06", "mllw_feet": 4.967},
        {"station_id": station_id, "datetime": "2020-08-19 12:12", "mllw_feet": 4.97},
        {"station_id": station_id, "datetime": "2020-08-19 12:18", "mllw_feet": 4.968},
        {"station_id": station_id, "datetime": "2020-08-19 12:24", "mllw_feet": 4.96},
        {"station_id": station_id, "datetime": "2020-08-19 12:30", "mllw_feet": 4.946},
        {"station_id": station_id, "datetime": "2020-08-19 12:36", "mllw_feet": 4.928},
        {"station_id": station_id, "datetime": "2020-08-19 12:42", "mllw_feet": 4.904},
        {"station_id": station_id, "datetime": "2020-08-19 12:48", "mllw_feet": 4.876},
        {"station_id": station_id, "datetime": "2020-08-19 12:54", "mllw_feet": 4.842},
        {"station_id": station_id, "datetime": "2020-08-19 13:00", "mllw_feet": 4.804},
        {"station_id": station_id, "datetime": "2020-08-19 13:06", "mllw_feet": 4.761},
        {"station_id": station_id, "datetime": "2020-08-19 13:12", "mllw_feet": 4.714},
        {"station_id": station_id, "datetime": "2020-08-19 13:18", "mllw_feet": 4.662},
        {"station_id": station_id, "datetime": "2020-08-19 13:24", "mllw_feet": 4.607},
        {"station_id": station_id, "datetime": "2020-08-19 13:30", "mllw_feet": 4.547},
        {"station_id": station_id, "datetime": "2020-08-19 13:36", "mllw_feet": 4.484},
        {"station_id": station_id, "datetime": "2020-08-19 13:42", "mllw_feet": 4.417},
        {"station_id": station_id, "datetime": "2020-08-19 13:48", "mllw_feet": 4.347},
        {"station_id": station_id, "datetime": "2020-08-19 13:54", "mllw_feet": 4.274},
        {"station_id": station_id, "datetime": "2020-08-19 14:00", "mllw_feet": 4.198},
        {"station_id": station_id, "datetime": "2020-08-19 14:06", "mllw_feet": 4.119},
        {"station_id": station_id, "datetime": "2020-08-19 14:12", "mllw_feet": 4.038},
        {"station_id": station_id, "datetime": "2020-08-19 14:18", "mllw_feet": 3.954},
        {"station_id": station_id, "datetime": "2020-08-19 14:24", "mllw_feet": 3.869},
        {"station_id": station_id, "datetime": "2020-08-19 14:30", "mllw_feet": 3.782},
        {"station_id": station_id, "datetime": "2020-08-19 14:36", "mllw_feet": 3.694},
        {"station_id": station_id, "datetime": "2020-08-19 14:42", "mllw_feet": 3.605},
        {"station_id": station_id, "datetime": "2020-08-19 14:48", "mllw_feet": 3.515},
        {"station_id": station_id, "datetime": "2020-08-19 14:54", "mllw_feet": 3.425},
        {"station_id": station_id, "datetime": "2020-08-19 15:00", "mllw_feet": 3.336},
        {"station_id": station_id, "datetime": "2020-08-19 15:06", "mllw_feet": 3.246},
        {"station_id": station_id, "datetime": "2020-08-19 15:12", "mllw_feet": 3.157},
        {"station_id": station_id, "datetime": "2020-08-19 15:18", "mllw_feet": 3.07},
        {"station_id": station_id, "datetime": "2020-08-19 15:24", "mllw_feet": 2.983},
        {"station_id": station_id, "datetime": "2020-08-19 15:30", "mllw_feet": 2.899},
        {"station_id": station_id, "datetime": "2020-08-19 15:36", "mllw_feet": 2.817},
        {"station_id": station_id, "datetime": "2020-08-19 15:42", "mllw_feet": 2.737},
        {"station_id": station_id, "datetime": "2020-08-19 15:48", "mllw_feet": 2.659},
        {"station_id": station_id, "datetime": "2020-08-19 15:54", "mllw_feet": 2.585},
        {"station_id": station_id, "datetime": "2020-08-19 16:00", "mllw_feet": 2.514},
        {"station_id": station_id, "datetime": "2020-08-19 16:06", "mllw_feet": 2.447},
        {"station_id": station_id, "datetime": "2020-08-19 16:12", "mllw_feet": 2.384},
        {"station_id": station_id, "datetime": "2020-08-19 16:18", "mllw_feet": 2.324},
        {"station_id": station_id, "datetime": "2020-08-19 16:24", "mllw_feet": 2.269},
        {"station_id": station_id, "datetime": "2020-08-19 16:30", "mllw_feet": 2.218},
        {"station_id": station_id, "datetime": "2020-08-19 16:36", "mllw_feet": 2.172},
        {"station_id": station_id, "datetime": "2020-08-19 16:42", "mllw_feet": 2.131},
        {"station_id": station_id, "datetime": "2020-08-19 16:48", "mllw_feet": 2.094},
        {"station_id": station_id, "datetime": "2020-08-19 16:54", "mllw_feet": 2.062},
        {"station_id": station_id, "datetime": "2020-08-19 17:00", "mllw_feet": 2.035},
        {"station_id": station_id, "datetime": "2020-08-19 17:06", "mllw_feet": 2.014},
        {"station_id": station_id, "datetime": "2020-08-19 17:12", "mllw_feet": 1.997},
        {"station_id": station_id, "datetime": "2020-08-19 17:18", "mllw_feet": 1.986},
        {"station_id": station_id, "datetime": "2020-08-19 17:24", "mllw_feet": 1.98},
        {"station_id": station_id, "datetime": "2020-08-19 17:30", "mllw_feet": 1.979},
        {"station_id": station_id, "datetime": "2020-08-19 17:36", "mllw_feet": 1.983},
        {"station_id": station_id, "datetime": "2020-08-19 17:42", "mllw_feet": 1.992},
        {"station_id": station_id, "datetime": "2020-08-19 17:48", "mllw_feet": 2.007},
        {"station_id": station_id, "datetime": "2020-08-19 17:54", "mllw_feet": 2.027},
        {"station_id": station_id, "datetime": "2020-08-19 18:00", "mllw_feet": 2.052},
        {"station_id": station_id, "datetime": "2020-08-19 18:06", "mllw_feet": 2.082},
        {"station_id": station_id, "datetime": "2020-08-19 18:12", "mllw_feet": 2.118},
        {"station_id": station_id, "datetime": "2020-08-19 18:18", "mllw_feet": 2.158},
        {"station_id": station_id, "datetime": "2020-08-19 18:24", "mllw_feet": 2.204},
        {"station_id": station_id, "datetime": "2020-08-19 18:30", "mllw_feet": 2.254},
        {"station_id": station_id, "datetime": "2020-08-19 18:36", "mllw_feet": 2.31},
        {"station_id": station_id, "datetime": "2020-08-19 18:42", "mllw_feet": 2.37},
        {"station_id": station_id, "datetime": "2020-08-19 18:48", "mllw_feet": 2.435},
        {"station_id": station_id, "datetime": "2020-08-19 18:54", "mllw_feet": 2.505},
        {"station_id": station_id, "datetime": "2020-08-19 19:00", "mllw_feet": 2.58},
        {"station_id": station_id, "datetime": "2020-08-19 19:06", "mllw_feet": 2.659},
        {"station_id": station_id, "datetime": "2020-08-19 19:12", "mllw_feet": 2.742},
        {"station_id": station_id, "datetime": "2020-08-19 19:18", "mllw_feet": 2.829},
        {"station_id": station_id, "datetime": "2020-08-19 19:24", "mllw_feet": 2.921},
        {"station_id": station_id, "datetime": "2020-08-19 19:30", "mllw_feet": 3.016},
        {"station_id": station_id, "datetime": "2020-08-19 19:36", "mllw_feet": 3.114},
        {"station_id": station_id, "datetime": "2020-08-19 19:42", "mllw_feet": 3.216},
        {"station_id": station_id, "datetime": "2020-08-19 19:48", "mllw_feet": 3.321},
        {"station_id": station_id, "datetime": "2020-08-19 19:54", "mllw_feet": 3.428},
        {"station_id": station_id, "datetime": "2020-08-19 20:00", "mllw_feet": 3.539},
        {"station_id": station_id, "datetime": "2020-08-19 20:06", "mllw_feet": 3.651},
        {"station_id": station_id, "datetime": "2020-08-19 20:12", "mllw_feet": 3.765},
        {"station_id": station_id, "datetime": "2020-08-19 20:18", "mllw_feet": 3.88},
        {"station_id": station_id, "datetime": "2020-08-19 20:24", "mllw_feet": 3.997},
        {"station_id": station_id, "datetime": "2020-08-19 20:30", "mllw_feet": 4.114},
        {"station_id": station_id, "datetime": "2020-08-19 20:36", "mllw_feet": 4.232},
        {"station_id": station_id, "datetime": "2020-08-19 20:42", "mllw_feet": 4.35},
        {"station_id": station_id, "datetime": "2020-08-19 20:48", "mllw_feet": 4.467},
        {"station_id": station_id, "datetime": "2020-08-19 20:54", "mllw_feet": 4.584},
        {"station_id": station_id, "datetime": "2020-08-19 21:00", "mllw_feet": 4.7},
        {"station_id": station_id, "datetime": "2020-08-19 21:06", "mllw_feet": 4.815},
        {"station_id": station_id, "datetime": "2020-08-19 21:12", "mllw_feet": 4.928},
        {"station_id": station_id, "datetime": "2020-08-19 21:18", "mllw_feet": 5.038},
        {"station_id": station_id, "datetime": "2020-08-19 21:24", "mllw_feet": 5.147},
        {"station_id": station_id, "datetime": "2020-08-19 21:30", "mllw_feet": 5.252},
        {"station_id": station_id, "datetime": "2020-08-19 21:36", "mllw_feet": 5.355},
        {"station_id": station_id, "datetime": "2020-08-19 21:42", "mllw_feet": 5.455},
        {"station_id": station_id, "datetime": "2020-08-19 21:48", "mllw_feet": 5.55},
        {"station_id": station_id, "datetime": "2020-08-19 21:54", "mllw_feet": 5.642},
        {"station_id": station_id, "datetime": "2020-08-19 22:00", "mllw_feet": 5.73},
        {"station_id": station_id, "datetime": "2020-08-19 22:06", "mllw_feet": 5.813},
        {"station_id": station_id, "datetime": "2020-08-19 22:12", "mllw_feet": 5.892},
        {"station_id": station_id, "datetime": "2020-08-19 22:18", "mllw_feet": 5.966},
        {"station_id": station_id, "datetime": "2020-08-19 22:24", "mllw_feet": 6.034},
        {"station_id": station_id, "datetime": "2020-08-19 22:30", "mllw_feet": 6.097},
        {"station_id": station_id, "datetime": "2020-08-19 22:36", "mllw_feet": 6.155},
        {"station_id": station_id, "datetime": "2020-08-19 22:42", "mllw_feet": 6.207},
        {"station_id": station_id, "datetime": "2020-08-19 22:48", "mllw_feet": 6.253},
        {"station_id": station_id, "datetime": "2020-08-19 22:54", "mllw_feet": 6.293},
        {"station_id": station_id, "datetime": "2020-08-19 23:00", "mllw_feet": 6.327},
        {"station_id": station_id, "datetime": "2020-08-19 23:06", "mllw_feet": 6.354},
        {"station_id": station_id, "datetime": "2020-08-19 23:12", "mllw_feet": 6.375},
        {"station_id": station_id, "datetime": "2020-08-19 23:18", "mllw_feet": 6.389},
        {"station_id": station_id, "datetime": "2020-08-19 23:24", "mllw_feet": 6.397},
        {"station_id": station_id, "datetime": "2020-08-19 23:30", "mllw_feet": 6.397},
        {"station_id": station_id, "datetime": "2020-08-19 23:36", "mllw_feet": 6.392},
        {"station_id": station_id, "datetime": "2020-08-19 23:42", "mllw_feet": 6.379},
        {"station_id": station_id, "datetime": "2020-08-19 23:48", "mllw_feet": 6.36},
        {"station_id": station_id, "datetime": "2020-08-19 23:54", "mllw_feet": 6.333},
        {"station_id": station_id, "datetime": "2020-08-20 00:00", "mllw_feet": 6.3},
        {"station_id": station_id, "datetime": "2020-08-20 00:06", "mllw_feet": 6.26},
    ]
