"""`macrostrat data` turns pipeline names into DVC targets."""

from pytest import raises
from test_pipelines import no_configured_workbook, workbook  # noqa: F401

from macrostrat.cli.data import _check_profile, _targets
from macrostrat.core.exc import MacrostratError


def test_targets_resolve_names_relative_to_the_root(tmp_path, monkeypatch):
    root = workbook(tmp_path)
    monkeypatch.chdir(root / "Stratigraphy")
    assert _targets(root, None) == []
    assert _targets(root, ["ngs", "GBDB"]) == [
        "--recursive",
        "Maps/NGS",
        "Stratigraphy/GBDB",
    ]
    with raises(MacrostratError):
        _targets(root, ["nothing"])


def test_check_profile_requires_the_named_profile(tmp_path, monkeypatch):
    root = workbook(tmp_path)
    aws = tmp_path / "aws-config"
    monkeypatch.setenv("AWS_CONFIG_FILE", str(aws))
    (root / ".dvc" / "config").write_text("[core]\n    remote = r\n")
    _check_profile(root)  # no profile named, nothing to check

    (root / ".dvc" / "config").write_text(
        "['remote \"r\"']\n    profile = macrostrat\n"
    )
    with raises(MacrostratError):
        _check_profile(root)
    aws.write_text(
        "[profile macrostrat]\nrequest_checksum_calculation = when_required\n"
    )
    _check_profile(root)
