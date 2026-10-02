from ..model import Check, JSONPath, Status

CHECKS = [
    Check(
        "api-v3-openapi",
        "api-v3",
        "/api/v3/openapi.json",
        [Status(200), JSONPath("openapi")],
    ),
]
