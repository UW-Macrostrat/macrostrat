"""Unit tests for convention-driven subsystem discovery (no database required)."""

from pathlib import Path

from macrostrat.schema_management.discovery import discover_chunks, parse_frontmatter


def test_parse_frontmatter_header_only():
    text = (
        "-- @subsystem: maps\n"
        "-- @depends-on: macrostrat, public\n"
        "-- @environments: development local\n"
        "/** doc comment */\n"
        "-- a plain note (not frontmatter)\n"
        "CREATE TABLE maps.sources (id int);\n"
        "-- @subsystem: ignored_after_sql\n"  # past the first SQL line → not parsed
    )
    assert parse_frontmatter(text) == {
        "subsystem": "maps",
        "depends-on": "macrostrat, public",
        "environments": "development local",
    }


def test_discover_chunks(tmp_path: Path):
    root = tmp_path

    # A single-file subsystem (frontmatter present).
    (root / "alpha.sql").write_text(
        "-- @subsystem: alpha\n-- @depends-on: base\nCREATE TABLE alpha.t (id int);\n"
    )
    # A loose .sql with no frontmatter → not a subsystem.
    (root / "loose.sql").write_text("CREATE TABLE loose (id int);\n")

    # A directory subsystem: _index.sql carries metadata AND real setup SQL.
    # The stray @environments must be IGNORED — environment is assigned externally.
    beta = root / "beta"
    beta.mkdir()
    (beta / "_index.sql").write_text(
        "-- @depends-on: alpha\n" "-- @environments: local\n" "CREATE SCHEMA beta;\n"
    )
    (beta / "01-tables.sql").write_text("CREATE TABLE beta.t (id int);\n")
    (beta / "02-views.sql").write_text("CREATE VIEW beta.v AS SELECT 1;\n")

    # A directory without _index.sql → not a subsystem.
    gamma = root / "gamma"
    gamma.mkdir()
    (gamma / "stuff.sql").write_text("CREATE TABLE gamma.t (id int);\n")

    chunks = {c.name: c for c in discover_chunks(root)}
    assert set(chunks) == {"alpha", "beta"}
    # Environment is assigned externally; unset by default, and the stray
    # @environments in beta's frontmatter is ignored.
    assert all(c.environments is None for c in chunks.values())

    alpha = chunks["alpha"]
    assert alpha.depends_on == ["base"]
    assert [p.name for p in alpha.provides] == ["alpha.sql"]

    beta_chunk = chunks["beta"]
    assert beta_chunk.depends_on == ["alpha"]
    # _index.sql is applied first (it's real content), then the rest by filename.
    assert [p.name for p in beta_chunk.provides] == [
        "_index.sql",
        "01-tables.sql",
        "02-views.sql",
    ]

    # The loader assigns environments by where it loads from — applied to all.
    dev = discover_chunks(root, environments=frozenset({"development"}))
    assert all(c.environments == frozenset({"development"}) for c in dev)
