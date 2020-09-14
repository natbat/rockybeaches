from datasette import hookimpl
from datasette.utils.asgi import Response


@hookimpl
def register_routes():
    return (
        # Homepage
        (r"^/$", lambda: Response.redirect("/us/pillar-point")),
    )
