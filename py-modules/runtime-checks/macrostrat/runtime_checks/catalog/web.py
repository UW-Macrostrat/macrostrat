import json

from ..model import Check, Compressed, Contains, ContentType, Redirect, Status

# Sift's routes and the pages they redirect to, mirroring `pages/sift/` in web.
# Unit 1 is in column 2 and group 1 in project 1, so those two follow the data.
SIFT_REDIRECTS = {
    "unit/1": "/columns/2",
    "column/1": "/columns/1",
    "group/1": "/projects/1/groups/1",
    "interval/1": "/lex/intervals/1",
    "strat_name_concept/1": "/lex/strat-concepts/1",
    "strat_name/1": "/lex/strat-names/1",
    "lithology/1": "/lex/lithologies/1",
    "environment/1": "/lex/environments/1",
    "economic/1": "/lex/economics/1",
    "definitions/lithologies": "/lex/lithologies",
    "explore": "/lex",
}

# v1 homepage sections and their v2 pages, mirroring `pages/index/+Head.ts` in web.
LEGACY_ANCHORS = {
    "about": "/about",
    "apps": "/community/apps",
    "api": "/docs/data-services",
    "people": "/about/people",
    "donate": "/about/support",
    "publications": "/community/publications",
}

CHECKS = [
    Check("web-home", "web", "/", [Status(200), Contains("<title>Macrostrat")]),
    Check("web-not-found", "web", "/this-is-a-404", [Status(404)]),
    # Responses from the Node app, which a proxy hop (Via) can leave uncompressed.
    Check("web-home-compressed", "web", "/", [Status(200), Compressed()]),
    Check(
        "web-page-context-compressed",
        "web",
        "/index.pageContext.json",
        [Status(200), ContentType("application/json"), Compressed()],
    ),
    *(
        Check(f"web-{page}", "web", f"/{page}")
        for page in ("map", "columns", "projects", "lex", "docs")
    ),
    Check("people-redirect", "web", "/people", [Redirect("/about/people")]),
    Check(
        "publications-redirect",
        "web",
        "/publications",
        [Redirect("/community/publications")],
    ),
    # `/sift/#/…` links: an inline head script turns the fragment into a path.
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
            [Redirect(target)],
        )
        for route, target in SIFT_REDIRECTS.items()
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
