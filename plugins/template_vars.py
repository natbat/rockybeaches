from datasette import hookimpl
import json


@hookimpl
def extra_template_vars():
    return {"json": json}
