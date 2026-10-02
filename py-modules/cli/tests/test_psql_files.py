"""`macrostrat db psql` runs psql in a container; local files must reach it."""

from pathlib import Path

from click import ClickException
from pytest import mark, raises

from macrostrat.cli.database import _local_file_flags, _psql_file_arguments


def test_file_options_in_every_spelling():
    args = ["-f", "a.sql", "-fb.sql", "--file=c.sql", "--file", "d.sql", "-o", "out"]
    assert _psql_file_arguments(args) == [
        Path(p) for p in ("a.sql", "b.sql", "c.sql", "d.sql", "out")
    ]


def test_stdin_and_other_options_name_no_file():
    assert _psql_file_arguments(["-f", "-", "-c", "SELECT 1", "-v", "x=1"]) == []


def test_files_are_mounted_at_their_own_paths(tmp_path, monkeypatch):
    work, elsewhere = tmp_path / "work", tmp_path / "elsewhere"
    work.mkdir()
    monkeypatch.chdir(work)

    flags = _local_file_flags(["-f", "../elsewhere/plan.sql", "-f", "sub/x.sql"])

    mounts = [flags[i + 1] for i, f in enumerate(flags) if f == "-v"]
    # The working directory, and the one outside it; `sub/` is already inside.
    assert mounts == [f"{work}:{work}", f"{elsewhere}:{elsewhere}"]
    assert flags[flags.index("-w") + 1] == str(work)


@mark.parametrize("cwd", ["/", "/usr/lib", "/etc"])
def test_a_directory_shadowing_the_containers_own_is_refused(cwd, monkeypatch):
    """Mounted at the same path, `/usr/lib` would replace the image's libraries."""
    monkeypatch.chdir(cwd)
    with raises(ClickException, match="container"):
        _local_file_flags([])


def test_a_file_in_a_system_directory_is_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with raises(ClickException, match="/etc"):
        _local_file_flags(["-f", "/etc/hosts"])
