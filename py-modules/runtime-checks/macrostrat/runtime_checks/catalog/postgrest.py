from ..model import Check, JSONPath, Status

CHECKS = [
    Check("postgrest-root", "postgrest", "/api/pg/", [Status(200), JSONPath("paths")]),
]
