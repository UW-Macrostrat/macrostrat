import json

from ..model import Check, Contains, Redirect, Status

# Sift's own routes; the id is irrelevant to the server, which renders a shell.
SIFT_ROUTES = (
    "unit/1",
    "column/1",
    "group/1",
    "interval/1",
    "strat_name_concept/1",
    "strat_name/1",
    "lithology/1",
    "environment/1",
    "economic/1",
    "definitions/lithologies",
    "explore",
)

# v1 homepage sections and their v2 pages, mirroring `pages/index/+Head.ts` in web.
LEGACY_ANCHORS = {
    "about": "/about",
    "apps": "/about/apps",
    "api": "/docs/data-services",
    "people": "/about/people",
    "donate": "/about/support",
    "publications": "/publications",
}

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
    # Browsers keep the fragment across this redirect, so `/sift/#/…` still arrives.
    Check("sift-trailing-slash", "web", "/sift/", [Redirect("/sift")]),
    *(
        Check(
            f"sift-{route.split('/')[0]}",
            "web",
            f"/sift/{route}",
            [Status(200), Contains("<title>Sift")],
        )
        for route in SIFT_ROUTES
    ),
    # `/#people` and the like: the homepage's head script carries each pair, and
    # each target page must load.
    *(
        Check(
            f"anchor-{anchor}",
            "web",
            target,
            [Status(200)],
            description=f"/#{anchor} → {target}",
        )
        for anchor, target in LEGACY_ANCHORS.items()
    ),
    Check(
        "anchor-redirect-script",
        "web",
        "/",
        [
            Status(200),
            *(
                Contains(f"{json.dumps(anchor)}:{json.dumps(target)}")
                for anchor, target in LEGACY_ANCHORS.items()
            ),
        ],
    ),
]
