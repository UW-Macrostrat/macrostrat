"""Route tests for the gateway image, run against tests/compose.yaml."""

import json
import os
import time
import unittest
import uuid
from http.client import HTTPConnection

API = int(os.environ.get("GATEWAY_TEST_API_PORT", 18080))
OLD_TILE_CACHE = int(os.environ.get("GATEWAY_TEST_OLD_TILES_PORT", 18081))
REPORT = int(os.environ.get("GATEWAY_TEST_REPORT_PORT", 18082))
VARNISH = int(os.environ.get("GATEWAY_TEST_VARNISH_PORT", 18083))
TILE_HOST = "tiles.test"


def request(port, path, method="GET", headers=None, host=None):
    headers = dict(headers or {})
    if host is not None:
        headers["Host"] = host
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, headers=headers)
    res = conn.getresponse()
    body = res.read()
    conn.close()
    return res, body


def echoed(port, path, **kwargs):
    res, body = request(port, path, **kwargs)
    assert res.status == 200, (path, res.status, body)
    return res, json.loads(body)


def unique(path):
    """A fresh URL, so no earlier test's cached response answers it."""
    sep = "&" if "?" in path else "?"
    return f"{path}{sep}n={uuid.uuid4().hex}"


def setUpModule():
    # Varnish marks Caddy healthy only after its first probe succeeds
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if all(
                request(port, "/api/health")[0].status == 200 for port in (API, REPORT)
            ) and all(
                request(port, "/legacy/version", host=TILE_HOST)[0].status == 200
                for port in (API, REPORT)
            ):
                if request(OLD_TILE_CACHE, "/legacy/version")[0].status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError("gateway did not become ready")


class APIRoutes(unittest.TestCase):
    def test_v3(self):
        _, data = echoed(API, "/api/v3/columns?id=1")
        self.assertEqual(data["service"], "api_v3")
        self.assertEqual(data["path"], "/columns?id=1")

    def test_v2(self):
        _, data = echoed(API, "/api/v2/units")
        self.assertEqual((data["service"], data["path"]), ("api_v2", "/units"))

    def test_unmatched_falls_back_to_v2(self):
        _, data = echoed(API, "/api/defs/intervals")
        self.assertEqual((data["service"], data["path"]), ("api_v2", "/defs/intervals"))

    def test_knowledge_graph(self):
        _, data = echoed(API, "/api/v3/knowledge-graph/search")
        self.assertEqual((data["service"], data["path"]), ("kg", "/search"))

    def test_health(self):
        res, body = request(API, "/api/health")
        self.assertEqual((res.status, body), (200, b"OK"))

    def test_version(self):
        res, data = echoed(API, "/api/gateway/version")
        self.assertEqual(data["service"], "api-gateway")
        self.assertEqual(res.getheader("Cache-Control"), "no-store")

    def test_legacy_raster_tiles(self):
        _, data = echoed(API, "/api/v2/maps/burwell/emphasized/12/986/1435/tile.png")
        self.assertEqual(data["service"], "tilehost")
        self.assertEqual(data["path"], "/carto/12/986/1435.png")
        self.assertEqual(data["headers"]["host"], "tilehost:8000")

    def test_task_routes_bypass_cache(self):
        res, _ = echoed(API, "/api/v3/tasks/list")
        self.assertEqual(res.getheader("X-Cache"), "bypass")

    def test_responses_are_cached(self):
        path = unique("/api/v3/columns")
        first, _ = echoed(API, path)
        second, _ = echoed(API, path)
        self.assertEqual(first.getheader("X-Cache"), "miss")
        self.assertEqual(second.getheader("X-Cache"), "hit")

    def test_v2_cookies_dropped(self):
        _, data = echoed(API, "/api/v2/units", headers={"Cookie": "access_token=abc"})
        self.assertNotIn("cookie", data["headers"])

    def test_cors_and_server_headers(self):
        res, _ = echoed(API, unique("/api/v3/columns"))
        self.assertEqual(res.getheader("Access-Control-Allow-Origin"), "*")
        self.assertIsNone(res.getheader("Server"))


class PostgRESTRoutes(unittest.TestCase):
    def test_schema_profiles(self):
        for path, schema in [
            ("/api/v3/macrostrat/pg/units", "macrostrat_api"),
            ("/api/v3/map-ingestion/pg/sources", "map_ingestion_api"),
            ("/api/v3/knowledge-graph/pg/runs", "macrostrat_api"),
            ("/api/pg/units", "macrostrat_api"),
        ]:
            with self.subTest(path=path):
                _, data = echoed(API, unique(path))
                self.assertEqual(data["service"], "postgrest")
                self.assertTrue(data["path"].startswith("/" + path.split("/")[-1]))
                self.assertEqual(data["headers"]["accept-profile"], schema)
                self.assertEqual(data["headers"]["content-profile"], schema)

    def test_content_range_renamed(self):
        # Varnish drops Content-Range from a 200, as deployed; clients read X-Data-Range
        res, _ = echoed(API, unique("/api/v3/macrostrat/pg/units"))
        self.assertEqual(res.getheader("X-Data-Range"), "0-9/100")

    def test_cookie_becomes_authorization(self):
        _, data = echoed(
            API, "/api/v3/macrostrat/pg/units", headers={"Cookie": "access_token=abc"}
        )
        self.assertEqual(data["headers"]["authorization"], "abc")
        self.assertNotIn("cookie", data["headers"])

    def test_authorization_header_wins(self):
        _, data = echoed(
            API,
            "/api/v3/macrostrat/pg/units",
            headers={"Cookie": "access_token=abc", "Authorization": "Bearer xyz"},
        )
        self.assertEqual(data["headers"]["authorization"], "Bearer xyz")

    def test_trailing_slash_redirect_keeps_api_prefix(self):
        res, _ = request(API, "/api/v3/macrostrat/pg")
        self.assertEqual(res.status, 301)
        # Relative, so it resolves to /api/v3/macrostrat/pg/
        self.assertEqual(res.getheader("Location"), "pg/")


def tile(path, client=None, port=API, host=TILE_HOST, **headers):
    """A request to the tile host, relayed by an edge proxy for `client`."""
    if client is not None:
        headers["X-Forwarded-For"] = client
    return request(port, path, headers=headers, host=host)


def tile_echo(path, **kwargs):
    res, body = tile(path, **kwargs)
    assert res.status == 200, (path, res.status, body)
    return res, json.loads(body)


def ban(expression):
    res, body = request(
        VARNISH, "/", method="BAN", headers={"X-Ban-Expression": expression}
    )
    assert res.status == 200, body


class TileHost(unittest.TestCase):
    def test_mvt_goes_to_api_v3_without_extension(self):
        _, data = tile_echo("/map/carto/3/2/1.mvt?x=1")
        self.assertEqual(
            (data["service"], data["path"]), ("api_v3", "/map/carto/3/2/1?x=1")
        )

    def test_png_goes_to_legacy(self):
        _, data = tile_echo(unique("/carto/3/2/1.png"))
        self.assertEqual(data["service"], "tileserver_legacy")
        self.assertTrue(data["path"].startswith("/carto/3/2/1.png?"))

    def test_raster_png_goes_to_api_v3(self):
        _, data = tile_echo(unique("/rasters/relief/3/2/1.png"))
        self.assertEqual(data["service"], "api_v3")

    def test_index_goes_to_legacy(self):
        _, data = tile_echo("/")
        self.assertEqual((data["service"], data["path"]), ("tileserver_legacy", "/"))

    def test_legacy_status_routes(self):
        _, data = tile_echo("/legacy/version")
        self.assertEqual(
            (data["service"], data["path"]), ("tileserver_legacy", "/version")
        )

    def test_tileserver_routes_allowed(self):
        for path in (
            "/carto/3/2/1",
            "/carto-slim/3/2/1.mvt",
            "/carto/tilejson.json",
            "/map/3/2/1?source_id=1",
            "/map/sgmc/3/2/1",
            "/map/sgmc/tilejson.json",
            "/carto/rotation-models",
            "/regions/tiles/3/2/1",
            "/search/units/tiles/3/2/1",
            "/cog/info?url=x",
            "/rasters/layer/relief/tilejson.json",
            "/cache/footprints/1/1/1",
            "/version",
        ):
            with self.subTest(path=path):
                _, data = tile_echo(unique(path))
                self.assertEqual(data["service"], "api_v3")
                self.assertEqual(
                    data["path"].split("?")[0], path.split("?")[0].removesuffix(".mvt")
                )

    def test_other_api_routes_refused(self):
        for path in (
            "/columns",
            "/regions",
            "/regions/1",
            "/map/sgmc/legend",
            "/dev/match/liths",
            "/cache/flush",
            "/carto/3/2",
            "/api/v3/columns",
        ):
            with self.subTest(path=path):
                res, body = tile(path)
                self.assertEqual(res.status, 404)
                self.assertIn(b"/api/v3", body)

    def test_other_hosts_are_the_api(self):
        _, data = echoed(API, "/api/v3/columns")
        self.assertEqual((data["service"], data["path"]), ("api_v3", "/columns"))

    def test_one_entry_per_tile_across_hosts(self):
        path = unique("/carto/3/2/1")
        first, _ = tile_echo(path)
        second, _ = echoed(API, "/api/v3" + path)
        self.assertEqual(
            (first.getheader("X-Cache"), second.getheader("X-Cache")), ("miss", "hit")
        )

    def test_api_responses_keyed_by_host(self):
        path = unique("/carto/tilejson.json")
        tile_echo(path)
        res, _ = echoed(API, "/api/v3" + path)
        self.assertEqual(res.getheader("X-Cache"), "miss")

    def test_tile_cookies_dropped(self):
        path = unique("/api/v3/carto/3/2/1")
        _, data = echoed(API, path, headers={"Cookie": "access_token=abc"})
        self.assertNotIn("cookie", data["headers"])
        res, _ = echoed(API, path, headers={"Cookie": "access_token=abc"})
        self.assertEqual(res.getheader("X-Cache"), "hit")

    def test_guarded_map_tiles_cached_despite_token(self):
        path = unique("/map/sgmc/3/2/1")
        tile_echo(path, Authorization="Bearer a")
        res, _ = tile_echo(path, Authorization="Bearer b")
        self.assertEqual(res.getheader("X-Cache"), "hit")

    def test_high_zoom_bypasses_cache(self):
        for get in (lambda p: tile_echo(p), lambda p: echoed(API, "/api/v3" + p)):
            path = unique("/carto/15/2/1")
            get(path)
            res, _ = get(path)
            self.assertEqual(res.getheader("X-Cache"), "bypass")

    def test_cors_restated_on_delivery(self):
        res, _ = tile_echo(unique("/carto/3/2/1.png"), Origin="https://x.org")
        self.assertEqual(res.getheader("Access-Control-Allow-Origin"), "*")

    def test_relayed_ban_refused(self):
        headers = {"X-Ban-Expression": "obj.http.X-Ban-Url ~ ^/"}
        for host, path in ((TILE_HOST, "/carto/3/2/1"), (None, "/api/v3/columns")):
            with self.subTest(host=host):
                res, _ = request(API, path, method="BAN", host=host, headers=headers)
                self.assertEqual(res.status, 403)


class CacheStorage(unittest.TestCase):
    def test_tile_ban_spares_api_responses(self):
        tile_path = unique("/carto/3/2/1")
        api_path = unique("/api/v3/columns")
        tile_echo(tile_path)
        echoed(API, api_path)
        ban("obj.http.X-Cache-Profile != api")
        self.assertEqual(tile_echo(tile_path)[0].getheader("X-Cache"), "miss")
        self.assertEqual(echoed(API, api_path)[0].getheader("X-Cache"), "hit")

    def test_url_ban_reaches_both_prefixes(self):
        vector = unique("/carto/3/2/1")
        image = unique("/carto/3/2/1.png")
        tile_echo(vector)
        tile_echo(image)
        ban("obj.http.X-Ban-Url ~ ^/(?:v3/|legacy-tiles/)?(?:carto)/")
        self.assertEqual(tile_echo(vector)[0].getheader("X-Cache"), "miss")
        self.assertEqual(tile_echo(image)[0].getheader("X-Cache"), "miss")


class OldTileCache(unittest.TestCase):
    """tiles.vcl, kept while the cluster still runs the separate tile cache."""

    def test_routes(self):
        _, data = echoed(OLD_TILE_CACHE, "/map/carto/3/2/1.mvt?x=1")
        self.assertEqual(
            (data["service"], data["path"]), ("tileserver_core", "/map/carto/3/2/1?x=1")
        )
        _, data = echoed(OLD_TILE_CACHE, unique("/carto/3/2/1.png"))
        self.assertEqual(data["service"], "tileserver_legacy")
        self.assertEqual(request(OLD_TILE_CACHE, "/columns")[0].status, 404)

    def test_tile_ban_expression_applies(self):
        # API v3's total flush, before and after the combined cache
        path = unique("/carto/3/2/1")
        echoed(OLD_TILE_CACHE, path)
        res, body = request(
            OLD_TILE_CACHE,
            "/",
            method="BAN",
            headers={"X-Ban-Expression": "obj.http.X-Cache-Profile != api"},
        )
        self.assertEqual(res.status, 200, body)
        self.assertEqual(echoed(OLD_TILE_CACHE, path)[0].getheader("X-Cache"), "miss")


def client_ipv4():
    n = uuid.uuid4().int
    return f"198.18.{n % 256}.{(n >> 8) % 256}"


def client_ipv6_net():
    n = uuid.uuid4().hex
    return f"2001:db8:{n[:4]}:{n[4:8]}"


def statuses(n, client, port=API):
    return [tile(unique("/carto/3/2/1.png"), client, port)[0].status for _ in range(n)]


class RenderThrottle(unittest.TestCase):
    """TILE_THROTTLE_BURST is 5 in tests/compose.yaml."""

    def test_sixth_miss_is_refused(self):
        client = client_ipv4()
        self.assertEqual(statuses(5, client), [200] * 5)
        res, body = tile(unique("/carto/3/2/1.png"), client)
        self.assertEqual(res.status, 429)
        self.assertEqual(res.getheader("X-Throttle"), "deny")
        self.assertEqual(res.getheader("Retry-After"), "600")
        self.assertIn(b"contact@macrostrat.org", body)

    def test_api_tile_routes_are_counted(self):
        client = client_ipv4()
        codes = [
            request(
                API, unique("/api/v3/carto/3/2/1"), headers={"X-Forwarded-For": client}
            )[0].status
            for _ in range(6)
        ]
        self.assertEqual(codes[5], 429)

    def test_raster_reads_are_counted(self):
        client = client_ipv4()
        codes = [tile(unique("/cog/info?url=x"), client)[0].status for _ in range(6)]
        self.assertEqual(codes[5], 429)

    def test_api_responses_are_not_counted(self):
        client = client_ipv4()
        codes = [
            request(
                API, unique("/api/v3/columns"), headers={"X-Forwarded-For": client}
            )[0].status
            for _ in range(10)
        ]
        self.assertEqual(codes, [200] * 10)

    def test_refused_client_still_gets_cached_tiles(self):
        client = client_ipv4()
        path = unique("/carto/3/2/1.png")
        tile(path, client_ipv4())
        statuses(6, client)
        self.assertEqual(tile(path, client)[0].status, 200)

    def test_clients_are_counted_apart(self):
        statuses(6, client_ipv4())
        self.assertEqual(statuses(1, client_ipv4()), [200])

    def test_cache_hits_are_not_counted(self):
        client = client_ipv4()
        path = unique("/carto/3/2/1.png")
        self.assertEqual([tile(path, client)[0].status for _ in range(10)], [200] * 10)

    def test_ipv6_counts_by_64(self):
        net = client_ipv6_net()
        codes = [
            tile(unique("/carto/3/2/1.png"), f"{net}:{i:x}:0:0:{i + 1:x}")[0].status
            for i in range(6)
        ]
        self.assertEqual(codes[5], 429)

    def test_forged_entries_do_not_reset_the_count(self):
        client = client_ipv4()
        codes = [
            tile(unique("/carto/3/2/1.png"), f"{client_ipv4()}, {client}")[0].status
            for _ in range(6)
        ]
        self.assertEqual(codes[5], 429)

    def test_client_header_cannot_be_forged(self):
        client = client_ipv4()
        codes = [
            tile(
                unique("/carto/3/2/1.png"),
                client,
                **{"X-Gateway-Client": client_ipv4()},
            )[0].status
            for _ in range(6)
        ]
        self.assertEqual(codes[5], 429)

    def test_internal_callers_are_exempt(self):
        codes = [tile(unique("/carto/3/2/1.png"))[0].status for _ in range(6)]
        self.assertEqual(codes, [200] * 6)

    def test_client_cannot_set_the_mark(self):
        res, _ = tile(
            unique("/carto/3/2/1.png"), client_ipv4(), **{"X-Throttle": "deny"}
        )
        self.assertEqual(res.status, 200)
        self.assertIsNone(res.getheader("X-Throttle"))


class RenderThrottleReport(unittest.TestCase):
    """TILE_THROTTLE_MODE=report marks over-limit clients but serves them."""

    def test_sixth_miss_is_marked_and_served(self):
        client = client_ipv4()
        statuses(5, client, REPORT)
        res, body = tile(unique("/carto/3/2/1.png"), client, REPORT)
        self.assertEqual(res.status, 200)
        self.assertEqual(res.getheader("X-Throttle"), "would-deny")
        body = json.loads(body)
        self.assertEqual(body["service"], "tileserver_legacy")
        self.assertNotIn("x-throttle-client", body["headers"])


if __name__ == "__main__":
    unittest.main()
