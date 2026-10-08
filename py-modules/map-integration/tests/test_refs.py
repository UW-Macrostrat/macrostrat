"""Map references: parsing citations, matching `macrostrat.refs`, writing links,
and the combined list `map_bounds.polygon_refs_for` serves."""

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.refs import (
    Reference,
    normalize_doi,
    parse_citation,
    place_links,
    resolve_refs,
    same_reference,
    write_links,
)

SOURCE_ID = 999201

UTAH = (
    "Hintze, L.F., Willis, G.C., and Laes, D.Y.M., Sprinkel, D.A., and Brown, K.D.,"
    " 2000, Digital Geologic Map of Utah: Utah Geological Survey Map M-179DM,"
    " scale 1:500,000."
)


def test_parse_citation():
    ref = parse_citation(UTAH, doi="https://doi.org/10.34191/M-179dm")
    assert ref.author.startswith("Hintze, L.F.") and ref.author.endswith("Brown, K.D.")
    assert ref.pub_year == 2000
    assert ref.ref.startswith("Digital Geologic Map of Utah")
    assert ref.doi == "10.34191/m-179dm"


def test_parse_citation_with_edition():
    ref = parse_citation(
        "Indiana Geological Survey, 1995 (latest update 2011), Bedrock Geology of Indiana"
    )
    assert (ref.author, ref.pub_year) == ("Indiana Geological Survey", 1995)
    assert ref.ref == "Bedrock Geology of Indiana"


@pytest.mark.parametrize(
    "text, author, year, ref",
    [
        (
            "Barnes, V.E., [1952?], Geologic map of the Blowout quadrangle",
            "Barnes, V.E.",
            1952,
            "Geologic map of the Blowout quadrangle",
        ),
        (
            "Fisher, D.W. 1977. Correlation of the Hadrynian, Cambrian, and Ordovician",
            "Fisher, D.W",
            1977,
            "Correlation of the Hadrynian, Cambrian, and Ordovician",
        ),
    ],
)
def test_parse_citation_variants(text, author, year, ref):
    parsed = parse_citation(text)
    assert (parsed.author, parsed.pub_year, parsed.ref) == (author, year, ref)


def test_parse_citation_without_year():
    assert (
        parse_citation("Digital bedrock data downloaded from Maine Office of GIS")
        is None
    )


@pytest.mark.parametrize(
    "doi", ["doi: 10.3133/ds1052", "https://doi.org/10.3133/DS1052", "10.3133/ds1052"]
)
def test_normalize_doi(doi):
    assert normalize_doi(doi) == "10.3133/ds1052"


def test_same_reference():
    a = parse_citation(
        "Love, J.D., and Christiansen, A.C., 1985, Geologic map of Wyoming:"
        " U.S. Geological Survey, 3 sheets, scale 1:500,000."
    )
    b = parse_citation(
        "Love, J.D. & Christiansen, A.C., 1985, Geologic map of Wyoming:"
        " U.S. Geological Survey, scale 1:500,000"
    )
    assert same_reference(a, b)
    # Another edition is another publication
    c = parse_citation(
        "Love, J.D., and Christiansen, A.C., 1979, Geologic map of Wyoming"
    )
    assert not same_reference(a, c)


def test_place_links_takes_the_highest_uniform_level():
    features = [
        # Map 1: one source throughout
        (1, 10, 100, "a"),
        (1, 11, 101, "a"),
        # Map 2: unit 20 uniform, unit 21 split, unit 22 with an unknown source
        (2, 20, 200, "b"),
        (2, 20, 201, "b"),
        (2, 21, 210, "b"),
        (2, 21, 211, "c"),
        (2, 22, 220, "c"),
        (2, 22, 221, None),
    ]
    placed = place_links(features, "data-from")
    assert placed["map"] == [(1, "a", "data-from")]
    assert placed["legend"] == [(20, "b", "data-from")]
    assert placed["polygon"] == [
        (210, "b", "data-from"),
        (211, "c", "data-from"),
        (220, "c", "data-from"),
    ]


@pytest.fixture(scope="module")
def db(test_db_base):
    with template_database(test_db_base, close_source_connections=True) as engine:
        _db = Database(engine)
        _db.run_sql(
            """
            INSERT INTO maps.sources (source_id, slug, scale)
            VALUES (:id, 'test-refs', 'large');
            INSERT INTO maps.polygons (source_id, scale, geom)
            SELECT :id, 'large', ST_Multi(ST_MakeEnvelope(x, 0, x + 1, 1, 4326))
            FROM generate_series(0, 1) x;
            INSERT INTO maps.legend (source_id, name) VALUES (:id, 'Qs');
            INSERT INTO maps.map_legend (map_id, legend_id)
            SELECT p.map_id, l.legend_id FROM maps.polygons p, maps.legend l
            WHERE p.source_id = :id AND l.source_id = :id;
            """,
            dict(id=SOURCE_ID),
            raise_errors=True,
        )
        _db.session.commit()
        yield _db


def _polygons(db) -> list[int]:
    return [
        r.map_id
        for r in db.run_query(
            "SELECT map_id FROM maps.polygons WHERE source_id = :id ORDER BY map_id",
            dict(id=SOURCE_ID),
        )
    ]


def test_resolve_refs_matches_existing(db):
    first = parse_citation(UTAH, doi="10.34191/M-179dm")
    ids = resolve_refs(db, [first])
    # The same DOI under a different spelling, and the same text without a DOI
    again = resolve_refs(
        db,
        [
            Reference(first.author, 2000, "Another title", doi="doi: 10.34191/m-179DM"),
            Reference(first.author.upper(), 2000, first.ref + "  "),
        ],
    )
    assert set(again.values()) == {ids[first]}
    db.session.rollback()


def test_links_combine_levels(db):
    utah = parse_citation(UTAH)
    nabesna = Reference("Richter, D.H.", 1976, "Geologic map of the Nabesna quadrangle")
    ids = resolve_refs(db, [utah, nabesna])
    legend_id = db.run_query(
        "SELECT legend_id FROM maps.legend WHERE source_id = :id", dict(id=SOURCE_ID)
    ).scalar()
    first, second = _polygons(db)

    write_links(
        db,
        "map",
        [(SOURCE_ID, ids[utah], "original")],
        keys=[SOURCE_ID],
        ref_types=["original"],
    )
    # The same reference at a second level is listed once
    write_links(
        db,
        "legend",
        [(legend_id, ids[utah], "original")],
        keys=[legend_id],
        ref_types=["original"],
    )
    write_links(
        db,
        "polygon",
        [(first, ids[nabesna], "data-from")],
        keys=[first, second],
        ref_types=["data-from"],
    )

    rows = db.run_query(
        "SELECT ref_type, label, citation FROM map_bounds.polygon_refs_for(:id)",
        dict(id=first),
    ).all()
    assert [(r.ref_type, r.label) for r in rows] == [
        ("original", "Original"),
        ("data-from", "Data from"),
    ]
    assert rows[1].citation == (
        "Richter, D.H., 1976, Geologic map of the Nabesna quadrangle"
    )
    assert [
        r.ref_type
        for r in db.run_query(
            "SELECT ref_type FROM map_bounds.polygon_refs_for(:id)", dict(id=second)
        )
    ] == ["original"]
    db.session.rollback()


def test_write_links_replaces_only_its_types(db):
    utah = parse_citation(UTAH)
    ids = resolve_refs(db, [utah])
    write_links(
        db,
        "map",
        [(SOURCE_ID, ids[utah], "original"), (SOURCE_ID, ids[utah], "compiled-in")],
        keys=[SOURCE_ID],
        ref_types=["original", "compiled-in"],
    )
    removed, written = write_links(
        db, "map", [], keys=[SOURCE_ID], ref_types=["compiled-in"]
    )
    assert (removed, written) == (1, 0)
    remaining = (
        db.run_query(
            "SELECT ref_type FROM maps.map_refs WHERE source_id = :id",
            dict(id=SOURCE_ID),
        )
        .scalars()
        .all()
    )
    assert remaining == ["original"]
    db.session.rollback()
