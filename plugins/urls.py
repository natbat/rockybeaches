from datasette import hookimpl
from datasette.utils.asgi import Response


async def place_page(datasette, request, scope, send, receive):
    slug = request.url_vars["slug"]
    internal_path = "/data/places/{}".format(slug)
    new_scope = dict(scope, path=internal_path, raw_path=internal_path.encode("utf-8"))
    await datasette.app()(new_scope, receive, send)


@hookimpl
def register_routes():
    return (
        # Homepage
        (r"^/$", lambda: Response.redirect("/us/pillar-point")),
        # country/slug - US only for the moment
        (r"^/us/(?P<slug>[^/]+)$", place_page),
    )
