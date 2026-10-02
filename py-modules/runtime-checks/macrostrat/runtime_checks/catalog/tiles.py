from ..model import Check, ContentType, JSONPath, NonEmpty, Status

CHECKS = [
    Check("tiles-openapi", "tiles", "/openapi.json", [Status(200), JSONPath("paths")]),
    *(
        Check(
            f"tiles-{layer}",
            "tiles",
            f"/{layer}/3/1/2",
            [Status(200), ContentType("application/x-protobuf"), NonEmpty()],
        )
        for layer in ("carto", "carto-slim")
    ),
]
