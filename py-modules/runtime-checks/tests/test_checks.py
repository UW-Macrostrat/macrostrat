import httpx
from pytest import mark

from macrostrat.runtime_checks import (
    CATALOG,
    Check,
    Contains,
    ContentType,
    JSONPath,
    Redirect,
    Status,
    run_checks,
)
from macrostrat.runtime_checks.local import STORAGE_ROUTES
from macrostrat.runtime_checks.report import to_json, write_junit
from macrostrat.runtime_checks.runner import SERVICE_HOSTS

ROUTES = {
    "/": (200, {"content-type": "text/html"}, "<title>Macrostrat</title>"),
    "/data": (200, {"content-type": "application/json"}, '{"a": {"b": [{"c": 1}]}}'),
    "/old": (301, {"location": "/new"}, ""),
    "/downgrade": (301, {"location": "http://example.org/new"}, ""),
    "/new": (200, {}, "new"),
}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/down":
        raise httpx.ConnectError("refused", request=request)
    code, headers, body = ROUTES.get(request.url.path, (404, {}, ""))
    return httpx.Response(code, headers=headers, text=body)


def run(*checks, hosts=None):
    hosts = hosts or {"base_url": "https://example.org", "tiles_url": None}
    return run_checks(checks, hosts, transport=httpx.MockTransport(handler))


def outcome(check):
    (result,) = run(check)
    return result.status, result.detail


@mark.parametrize(
    "check",
    [
        Check("home", "web", "/", [Status(200), Contains("<title>Macrostrat")]),
        Check("json", "web", "/data", [JSONPath("a.b[0].c", equals=1)]),
        Check("type", "web", "/data", [ContentType("application/json")]),
        Check("redirect", "web", "/old", [Redirect("/new")]),
        Check("followed", "web", "/old", [Status(200), Contains("new")]),
        Check("missing", "web", "/nothing", [Status(404)]),
    ],
)
def test_passing(check):
    assert outcome(check)[0] == "ok"


@mark.parametrize(
    "check,detail",
    [
        (Check("status", "web", "/nothing"), "status 404, expected 200"),
        (Check("text", "web", "/", [Contains("Sift")]), "body lacks 'Sift'"),
        (Check("path", "web", "/data", [JSONPath("a.b[1].c")]), "no a.b[1].c in body"),
        (Check("not-json", "web", "/", [JSONPath("a")]), "body is not JSON"),
        (Check("target", "web", "/old", [Redirect("/other")]), "expected /other"),
        (Check("scheme", "web", "/downgrade", [Redirect("/new")]), "changing scheme"),
        (Check("down", "web", "/down"), "ConnectError: refused"),
    ],
)
def test_failing(check, detail):
    status, actual = outcome(check)
    assert status == "fail"
    assert detail in actual


def test_scheme_change_allowed():
    check = Check("scheme", "web", "/downgrade", [Redirect("/new", same_scheme=False)])
    assert outcome(check)[0] == "ok"


def test_severity():
    assert outcome(Check("soft", "web", "/nothing", severity="warn"))[0] == "warn"


def test_unconfigured_host_warns_once():
    results = run(Check("a", "tiles", "/a"), Check("b", "tiles", "/b"))
    assert [(r.name, r.status) for r in results] == [("tiles", "warn")]
    assert "2 checks skipped" in results[0].detail


def test_other_tiers_skipped():
    assert run(Check("browser", "web", "/", tier="browser")) == []


def test_results_keep_catalog_order():
    names = ["a", "b", "c"]
    results = run(*(Check(n, "web", "/") for n in names))
    assert [r.name for r in results] == names


def test_catalog_is_well_formed():
    checks = [*CATALOG, *STORAGE_ROUTES]
    names = [c.name for c in checks]
    assert len(names) == len(set(names))
    assert {c.service for c in checks} <= set(SERVICE_HOSTS)
    for check in CATALOG:
        assert check.path.startswith("/")


def test_reports(tmp_path):
    results = run(Check("ok", "web", "/"), Check("bad", "web", "/nothing"))
    assert '"status": "fail"' in to_json(results)
    path = tmp_path / "results.xml"
    write_junit(results, path)
    xml = path.read_text()
    assert 'failures="1"' in xml
    assert "status 404" in xml
