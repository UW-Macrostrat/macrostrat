from ..model import Check, Contains, Redirect, Status

CHECKS = [
    Check("web-home", "web", "/", [Status(200), Contains("<title>Macrostrat")]),
    Check("web-not-found", "web", "/this-is-a-404", [Status(404)]),
    *(
        Check(f"web-{page}", "web", f"/{page}")
        for page in ("map", "columns", "projects", "lex", "docs")
    ),
    Check("people-redirect", "web", "/people", [Redirect("/community/contributors")]),
    # Legacy `/sift/#/…` links are redirected by an inline script in the page head.
    Check(
        "sift-hash-redirect",
        "web",
        "/sift/",
        [Status(200), Contains("location.replace")],
    ),
]
