from ..model import Check, ContentType, JSONPath, NonEmpty, Status

CHECKS = [
    Check("api-v2-root", "api-v2", "/api/v2/", [Status(200), JSONPath("success")]),
    Check(
        "api-v2-column",
        "api-v2",
        "/api/v2/columns?col_id=17",
        [Status(200), JSONPath("success.data[0].col_id", equals=17)],
    ),
    # Redirects to the tileserver's raster route.
    Check(
        "api-v2-legacy-tile",
        "api-v2",
        "/api/v2/maps/burwell/emphasized/1/0/1/tile.png",
        [Status(200), ContentType("image/png"), NonEmpty()],
    ),
]
