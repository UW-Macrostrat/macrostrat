from io import BytesIO

from pytest import fixture, mark, raises

from macrostrat.loader_utils import LoadError, load_csv

SCHEMA = "loader_csv_test"


@fixture(scope="module")
def csv_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("tables") / "units.csv"
    path.write_text("Unit ID,Name,Name,Age\n1,Aoxi Fm,,12.5\n2,Baota Fm,x,\n")
    return path


def _types(result):
    return dict(zip(result.columns, result.types))


def test_dry_run_structure(csv_file):
    result = load_csv(None, csv_file, dry_run=True)
    assert result.table == "units"
    assert _types(result) == {
        "unit_id": "bigint",
        "name": "text",
        "name_2": "text",
        "age": "double precision",
    }
    assert result.rows == 2
    assert result.copied is None


def test_all_text(csv_file):
    result = load_csv(None, csv_file, all_text=True, dry_run=True)
    assert set(result.types) == {"text"}


def test_stream_needs_a_table():
    with raises(LoadError):
        load_csv(None, BytesIO(b"a\n1\n"), dry_run=True)


def test_missing_file(tmp_path):
    with raises(LoadError):
        load_csv(None, tmp_path / "absent.csv", dry_run=True)


@fixture(scope="module")
def scratch(empty_db):
    empty_db.run_sql(f"CREATE SCHEMA {SCHEMA}", raise_errors=True)
    try:
        yield empty_db
    finally:
        empty_db.run_sql(f"DROP SCHEMA {SCHEMA} CASCADE", raise_errors=True)


@mark.docker
def test_load_and_replace(scratch, csv_file):
    engine = scratch.engine
    result = load_csv(engine, csv_file, schema=SCHEMA)
    assert result.copied == 2
    rows = scratch.run_query(
        f"SELECT unit_id, name, age FROM {SCHEMA}.units ORDER BY unit_id"
    ).all()
    assert [tuple(r) for r in rows] == [(1, "Aoxi Fm", 12.5), (2, "Baota Fm", None)]
    # Release the session's locks; load_csv replaces on its own connection.
    scratch.session.commit()

    with raises(LoadError):
        load_csv(engine, csv_file, schema=SCHEMA)
    again = load_csv(engine, csv_file, schema=SCHEMA, replace=True)
    assert again.copied == 2

    stream = BytesIO(csv_file.read_bytes())
    appended = load_csv(engine, stream, schema=SCHEMA, table="units", append=True)
    assert appended.copied == 2
    assert scratch.run_query(f"SELECT count(*) FROM {SCHEMA}.units").scalar() == 4
