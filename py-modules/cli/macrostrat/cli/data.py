"""Move a workbook's DVC-tracked inputs, naming pipelines as `macrostrat run` does.

    macrostrat data pull ngs        # every input beneath Maps/NGS
    macrostrat data push            # everything not yet in the remote
    macrostrat data status [ngs]    # local and remote state
    macrostrat data setup           # the AWS profile the remote reads

DVC is launched, never imported. `pull` refuses to run without a target, and there
is deliberately no `gc`: `dvc gc --cloud` deletes remote objects other branches use.
"""

from __future__ import annotations

import re
from os import environ
from pathlib import Path
from subprocess import run as run_process

from rich import print
from typer import Argument, Exit, Typer

from macrostrat.core.exc import MacrostratError

from . import pipelines

app = Typer(no_args_is_help=True, short_help="Pull and push pipeline inputs (DVC)")

Targets = Argument(None, help="Pipeline names or paths", show_default=False)

_PROFILE = re.compile(r"^\s*profile\s*=\s*(\S+)\s*$", re.M)


def _root() -> Path:
    root = pipelines.find_workbook()
    if root is None:
        raise MacrostratError(
            "Not inside a workbook",
            details="Run this beneath a .dvc/ folder, or set sources.data_integration.",
        )
    return root


def _targets(root: Path, names: list[str] | None) -> list[str]:
    """`--recursive` and DVC targets relative to the root; nothing means everything."""
    if not names:
        return []
    targets = ["--recursive"]
    for name in names:
        path = pipelines.resolve(name)
        if path is None:
            raise MacrostratError(
                f"[item]{name}[/item] is not a pipeline or a path",
                details="`macrostrat run` lists the pipelines here.",
            )
        path = path.resolve()
        if not path.is_relative_to(root):
            raise MacrostratError(f"[item]{name}[/item] is outside the workbook {root}")
        targets.append(str(path.relative_to(root)))
    return targets


def _check_profile(root: Path):
    """Fail early when the remote names an AWS profile this machine lacks."""
    match = _PROFILE.search((root / ".dvc" / "config").read_text())
    if match is None:
        return
    profile = match.group(1)
    config = Path(environ.get("AWS_CONFIG_FILE", "~/.aws/config")).expanduser()
    if config.is_file() and f"[profile {profile}]" in config.read_text():
        return
    raise MacrostratError(
        f"The DVC remote reads AWS profile [item]{profile}[/item], which is missing",
        details="Write it with `macrostrat --env development data setup`.",
    )


def _dvc(root: Path, *args: str) -> int:
    cmd = ["dvc", *args]
    print(f"[dim]{' '.join(cmd)}[/dim]")
    return run_process(cmd, cwd=root).returncode


@app.command()
def pull(names: list[str] = Targets):
    """Fetch the inputs of one or more pipelines."""
    root = _root()
    if not names:
        pipelines.list_pipelines(root)
        raise MacrostratError(
            "Name what to pull",
            details="A bare pull fetches every dataset in the workbook.",
        )
    _check_profile(root)
    raise Exit(_dvc(root, "pull", *_targets(root, names)))


@app.command()
def push(names: list[str] = Targets):
    """Upload tracked content, for the named pipelines or the whole workbook."""
    root = _root()
    _check_profile(root)
    raise Exit(_dvc(root, "push", *_targets(root, names)))


@app.command()
def status(names: list[str] = Targets):
    """What has changed locally and what the remote lacks."""
    root = _root()
    _check_profile(root)
    targets = _targets(root, names)
    local = _dvc(root, "status", *targets)
    raise Exit(local or _dvc(root, "status", "--cloud", *targets))


@app.command()
def setup():
    """Write the AWS profile the remote reads: storage keys and Ceph checksum settings."""
    from .subsystems.storage import _export_radosgw_credentials, add_profile

    _export_radosgw_credentials()
    add_profile(uid="macrostrat", name="macrostrat")
