"""`macrostrat run` resolves pipelines in a workbook without importing them."""

from pathlib import Path

from pytest import fixture, raises

from macrostrat.cli import pipelines
from macrostrat.cli.pipelines import (
    Pipeline,
    command_for,
    discover,
    frontmatter,
    resolve,
    workbook_root,
)
from macrostrat.core.exc import MacrostratError


@fixture(autouse=True)
def no_configured_workbook(monkeypatch):
    """Keep the developer's `sources.data_integration` out of these tests."""
    monkeypatch.setattr(pipelines, "configured_workbook", lambda: None)


def workbook(tmp_path: Path) -> Path:
    """A workbook shaped like `data-integration`."""
    (tmp_path / ".dvc").mkdir()
    (tmp_path / "Makefile").write_text(
        "push:\n\tdvc push\n"
    )  # root helpers, not a pipeline

    ngs = tmp_path / "Maps" / "NGS"
    ngs.mkdir(parents=True)
    (ngs / "cli.py").write_text("")
    (ngs / "Makefile").write_text("")  # cli.py wins when both are present
    (ngs / "README.md").write_text("---\nsource: USGS\nstatus: staging\n---\n# NGS\n")
    (ngs / "sql").mkdir()

    gbdb = tmp_path / "Stratigraphy" / "GBDB"
    (gbdb / "legacy").mkdir(parents=True)
    (gbdb / "cli.py").write_text("")
    (gbdb / "legacy" / "cli.py").write_text("")  # kept as a record, never run

    eodp = tmp_path / "eodp-refs"
    eodp.mkdir()
    (eodp / "Makefile").write_text("")

    (tmp_path / "Maps" / "Japan").mkdir()  # data only, no entrypoint
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "cli.py").write_text("")
    return tmp_path


def test_discover_finds_runnable_directories_only(tmp_path):
    root = workbook(tmp_path)
    found = {p.path.relative_to(root).as_posix(): p for p in discover(root)}
    assert set(found) == {"Maps/NGS", "Stratigraphy/GBDB", "eodp-refs"}
    assert found["Maps/NGS"].entrypoint == "cli.py"
    assert found["Maps/NGS"].status == "staging"
    assert found["Stratigraphy/GBDB"].status is None
    assert found["eodp-refs"].entrypoint == "Makefile"


def test_workbook_root_walks_up_to_dvc(tmp_path):
    root = workbook(tmp_path)
    assert workbook_root(root / "Maps" / "NGS" / "sql") == root
    assert workbook_root(tmp_path.parent) is None


def test_resolve_by_name_is_case_insensitive(tmp_path):
    root = workbook(tmp_path)
    assert resolve("ngs", cwd=root / "Stratigraphy") == root / "Maps" / "NGS"
    assert resolve("GBDB", cwd=root) == root / "Stratigraphy" / "GBDB"
    assert resolve("japan", cwd=root) is None
    assert resolve("nothing", cwd=tmp_path.parent) is None


def test_resolve_falls_back_to_the_configured_workbook(tmp_path, monkeypatch):
    (tmp_path / "wb").mkdir()
    root = workbook(tmp_path / "wb")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(pipelines, "configured_workbook", lambda: root)
    assert resolve("ngs", cwd=elsewhere) == root / "Maps" / "NGS"


def test_resolve_prefers_an_existing_path(tmp_path, monkeypatch):
    root = workbook(tmp_path)
    monkeypatch.chdir(root)
    assert resolve("Maps/NGS") == Path("Maps/NGS")


def test_resolve_refuses_ambiguity(tmp_path):
    root = workbook(tmp_path)
    other = root / "Other" / "ngs"
    other.mkdir(parents=True)
    (other / "cli.py").write_text("")
    with raises(MacrostratError):
        resolve("NGS", cwd=root)


def test_command_for_each_entrypoint(tmp_path):
    root = workbook(tmp_path)
    cmd, cwd = command_for(root / "Maps" / "NGS", ["sources", "--apply"])
    assert cmd == ["uv", "run", "python", "cli.py", "sources", "--apply"]
    assert cwd == root / "Maps" / "NGS"

    cmd, cwd = command_for(root / "eodp-refs", ["all"])
    assert cmd == ["make", "-C", str(root / "eodp-refs"), "all"]
    assert cwd is None

    script = root / "Stratigraphy" / "GBDB" / "cli.py"
    cmd, cwd = command_for(script, [])
    assert cmd == ["uv", "run", "python", "cli.py"]
    assert cwd == script.parent

    with raises(MacrostratError):
        command_for(root / "Maps" / "Japan", [])


def test_frontmatter_reads_the_readme_header_only(tmp_path):
    d = tmp_path / "p"
    d.mkdir()
    (d / "README.md").write_text("# No frontmatter\n\nstatus: not this\n")
    assert frontmatter(d) == {}
    (d / "README.md").write_text('---\nstatus: "done"\nreceived_on: 2026-10-03\n---\n')
    assert frontmatter(d)["status"] == "done"
    (d / "cli.py").write_text("")
    pipeline = Pipeline.at(d)
    assert pipeline.status == "done"
    assert pipeline.matches("P")


def test_frontmatter_overrides_name_description_and_entrypoint(tmp_path):
    root = workbook(tmp_path)
    usgs = root / "Geochronology" / "USGS-Geochronology-Database"
    usgs.mkdir(parents=True)
    (usgs / "load.sh").write_text("")
    (usgs / "README.md").write_text(
        "---\nname: geochron\ndescription: USGS dates\nentrypoint: load.sh\n---\n"
    )
    found = {p.name: p for p in discover(root)}
    assert found["geochron"].description == "USGS dates"
    assert found["geochron"].entrypoint == "load.sh"
    assert resolve("geochron", cwd=root) == usgs
    assert resolve("USGS-Geochronology-Database", cwd=root) is None
    assert command_for(usgs, ["x"]) == (["./load.sh", "x"], usgs)


def test_declared_entrypoint_must_exist(tmp_path):
    root = workbook(tmp_path)
    (root / "eodp-refs" / "README.md").write_text("---\nentrypoint: gone.py\n---\n")
    with raises(MacrostratError):
        discover(root)
