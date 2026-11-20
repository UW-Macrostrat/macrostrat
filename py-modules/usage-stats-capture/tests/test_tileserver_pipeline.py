"""The tileserver pipeline's parsing and aggregation, database-free."""

from datetime import datetime, timedelta

from macrostrat.usage_stats_capture.pipelines.tileserver import (
    HEAVY_CLIENT_TILES_PER_HOUR,
    KEEP_LAYERS,
    SOURCES_FIELD,
    TileserverPipeline,
    aggregate,
    client_network,
    parse_sources,
    parse_tile_path,
    tag_heavy_clients,
)


def record(path, **extra):
    rec = {
        "RequestMethod": "GET",
        "RequestHost": "tiles.macrostrat.org",
        "RequestPath": path,
        "StartUTC": "2026-10-07T12:00:00.123456789Z",
        "ClientHost": "203.0.113.5",
    }
    rec.update(extra)
    return rec


class TestSourcesHeader:
    def test_ids(self):
        assert parse_sources("7,133,3401") == [7, 133, 3401]

    def test_absent_header_credits_nothing(self):
        assert parse_sources(None) == []
        assert parse_sources("") == []

    def test_garbage_tokens_are_skipped_not_fatal(self):
        assert parse_sources("7, x,133,,") == [7, 133]


class TestParse:
    def test_compilation_carto_is_kept_with_its_sources(self):
        row = TileserverPipeline().parse(
            record("/map/carto/6/15/23", **{SOURCES_FIELD: "133,3401"})
        )
        assert row["layer"] == "map/carto"
        assert row["sources"] == [133, 3401]
        assert (row["z"], row["x"], row["y"]) == (6, 15, 23)

    def test_legacy_carto_names_no_sources(self):
        row = TileserverPipeline().parse(record("/carto-slim/4/12/5.mvt"))
        assert row["layer"] == "carto-slim"
        assert row["sources"] == []

    def test_both_carto_routes_are_kept(self):
        assert {"carto", "carto-slim", "map/carto"} <= KEEP_LAYERS
        assert parse_tile_path("/map/carto/6/15/23")["layer"] == "map/carto"


class TestAggregate:
    def test_each_named_map_is_credited_per_day(self):
        base = dict(
            layer="map/carto",
            ext="",
            is_bot=False,
            referrer="",
            x_cache="hit",
            x_tile_cache="miss",
        )
        t = datetime(2026, 10, 7, 12)
        rows = [
            {**base, "z": 6, "x": 15, "y": 23, "time": t, "sources": [133, 3401]},
            {**base, "z": 6, "x": 15, "y": 24, "time": t, "sources": [3401]},
            {**base, "z": 6, "x": 15, "y": 24, "time": t, "sources": []},
        ]
        day_rows, loc_rows, source_rows = aggregate(rows)
        assert sum(r["num_requests"] for r in day_rows) == 3
        by_source = {r["source_id"]: r["num_requests"] for r in source_rows}
        assert by_source == {133: 1, 3401: 2}
        assert all(r["date"] == datetime(2026, 10, 7) for r in source_rows)

    def test_rows_without_sources_make_no_source_rows(self):
        rows = [
            dict(
                layer="carto",
                ext="mvt",
                is_bot=False,
                referrer="",
                x_cache="",
                x_tile_cache="",
                z=3,
                x=1,
                y=2,
                time=datetime(2026, 1, 1),
                sources=[],
            )
        ]
        assert aggregate(rows)[2] == []


def requests(client, n, start, span):
    step = span / max(n - 1, 1)
    return [
        {"client": client, "is_bot": False, "time": start + i * step} for i in range(n)
    ]


class TestHeavyClients:
    start = datetime(2026, 11, 12, 0)

    def test_ipv6_clients_count_by_64(self):
        assert client_network("2001:448a:9080:fbf:2ca6:8faa:5ab6:e68") == (
            "2001:448a:9080:fbf::/64"
        )
        assert client_network("203.0.113.5") == "203.0.113.5"
        assert client_network(None) is None

    def test_parse_carries_the_network(self):
        row = TileserverPipeline().parse(
            record("/carto-slim/14/2438/7481.mvt", ClientHost="2001:db8::1")
        )
        assert row["client"] == "2001:db8::/64"
        assert row["is_bot"] is False

    def test_only_the_heavy_client_is_tagged(self):
        hour = timedelta(hours=1)
        rows = requests("sweeper", HEAVY_CLIENT_TILES_PER_HOUR + 1, self.start, hour)
        rows += requests("person", 500, self.start, hour)
        tag_heavy_clients(rows)
        assert all(r["is_bot"] for r in rows if r["client"] == "sweeper")
        assert not any(r["is_bot"] for r in rows if r["client"] == "person")

    def test_limit_scales_with_the_batch_span(self):
        # 6,000 tiles in 20 minutes is 18,000 an hour; in 15, 24,000.
        assert not any(
            r["is_bot"]
            for r in tag_heavy_clients(
                requests("c", 6000, self.start, timedelta(minutes=20))
            )
        )
        assert all(
            r["is_bot"]
            for r in tag_heavy_clients(
                requests("c", 6000, self.start, timedelta(minutes=15))
            )
        )

    def test_short_batches_are_judged_over_fifteen_minutes(self):
        # A minute-long burst of 2,000 is under the 15-minute floor's 5,000.
        rows = requests("burst", 2000, self.start, timedelta(minutes=1))
        assert not any(r["is_bot"] for r in tag_heavy_clients(rows))

    def test_known_bots_stay_tagged(self):
        rows = requests("known", 3, self.start, timedelta(minutes=30))
        for r in rows:
            r["is_bot"] = True
        assert all(r["is_bot"] for r in tag_heavy_clients(rows))
