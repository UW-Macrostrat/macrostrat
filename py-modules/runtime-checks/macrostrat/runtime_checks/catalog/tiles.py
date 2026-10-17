from ..model import Check, ContentType, JSONPath, MaxElapsed, NonEmpty, Status

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
    # A cold render, as legacy clients get after an eviction. Zoom 4 reads the
    # small-scale partition; it took over 60 s while a cast blocked pruning.
    *(
        Check(
            f"tiles-{layer}-uncached",
            "tiles",
            f"/{layer}/4/3/6?cache=bypass",
            [
                Status(200),
                ContentType("application/x-protobuf"),
                NonEmpty(),
                MaxElapsed(5),
            ],
        )
        for layer in ("carto", "carto-slim")
    ),
]
