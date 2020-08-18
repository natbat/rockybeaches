from datasette import hookimpl
from datasette.utils.asgi import Response


@hookimpl
def register_routes():
    return ((r"^/$", lambda: Response.redirect("/data/places/pillar-point")),)
