# Rocky Beaches

[rockybeaches.com](https://www.rockybeaches.com/) helps you find places to go tidepooling, and figure out the best times to go.

The site was designed by Natalie Downe ([@natbat](https://twitter.com/natbat)) and built by Natalie Downe and Simon Willison ([@simonw](https://twitter.com/simonw)).

It uses data pulled from [iNaturalist](https://www.inaturalist.org/) and the [NOAA Tides & Currents API](https://tidesandcurrents.noaa.gov/web_services_info.html).

[Working tide stations](https://www.rockybeaches.com/data/noaa_stations_map?good__exact=1)

## Technology used

- [Datasette](https://datasette.io/) and [datasette-graphql](https://github.com/simonw/datasette-graphql)
- [sqlite-utils](https://sqlite-utils.readthedocs.io/)
- [yaml-to-sqlite](https://github.com/simonw/yaml-to-sqlite)
- [airtable-export](https://github.com/simonw/airtable-export)
- [astral](https://astral.readthedocs.io/)

## Development

Install dependencies (ideally into a Python virtual environment, e.g. one created with `pipenv shell`):

    pip install -r requirements.txt

Build the SQLite database from the YAML in `data/` plus data fetched from NOAA and iNaturalist:

    script/build

Run tests like this:

    script/test

Run the development server:

    datasette .
