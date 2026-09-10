"""Run a data pipeline with the active environment resolved into its own.

A **pipeline** is a directory in a workbook — a git repository whose large files are
DVC pointers, such as `data-integration` — holding either a Typer app named `cli.py`
or a `Makefile`. `macrostrat run` launches it, never imports it: the pipeline may
live in its own virtualenv with dependencies Macrostrat will never carry, or not be
Python at all. What Macrostrat contributes is the environment. The child receives

    MACROSTRAT_ENV           for a child that resolves config itself
    MACROSTRAT_DATABASE_URL  for a child that has no Macrostrat in it

so that `--env`, the remembered environment and its lapse rules all apply to the
pipeline exactly as they do to `macrostrat db`.

Pipelines are named by their directory, case-insensitively, and found by walking
the workbook that contains the current directory:

    macrostrat run                       # list what is here
    macrostrat run ngs sources --apply   # Maps/NGS/cli.py sources --apply
    macrostrat run Stratigraphy/GBDB     # a path works too, from anywhere

Macrostrat's configuration is read by the child but never extended for it — a
pipeline's own connection strings and paths belong to the pipeline.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from os import environ
from pathlib import Path
from subprocess import run as run_process

from rich import print
from rich.table import Table

from macrostrat.core import app
from macrostrat.core.exc import MacrostratError
from macrostrat.core.utils import env_text

#: What makes a directory runnable, in order of preference.
ENTRYPOINTS = ("cli.py", "Makefile")

#: Never descended into: tool state, environments, and `legacy/`, which the workbook
#: keeps as a record rather than as something to run.
SKIP_DIRS = frozenset({".venv", "__pycache__", "node_modules", "legacy"})

_STATUS = re.compile(r"^status:[ \t]*(.+?)[ \t]*$", re.M)


@dataclass(frozen=True)
class Pipeline:
    path: Path
    entrypoint: str
    status: str | None = None

    @property
    def name(self) -> str:
        return self.path.name

    def matches(self, name: str) -> bool:
        return self.path.name.lower() == name.lower()


def workbook_root(start: Path | None = None) -> Path | None:
    """The nearest enclosing directory that DVC has been initialized in."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".dvc").is_dir():
            return candidate
    return None


def readme_status(directory: Path) -> str | None:
    """The `status:` a pipeline's README declares in its frontmatter, if any."""
    readme = directory / "README.md"
    if not readme.is_file():
        return None
    text = readme.read_text(errors="replace")
    match = re.match(r"^---\n(.*?\n)---\n", text, re.S)
    if match is None:
        return None
    found = _STATUS.search(match.group(1))
    return found.group(1).strip("'\"") if found else None


def discover(root: Path) -> list[Pipeline]:
    """Every pipeline beneath `root`. A pipeline does not nest: once a directory is
    runnable, nothing below it is considered."""
    found: list[Pipeline] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        )
        directory = Path(dirpath)
        if directory == root:
            continue
        entrypoint = next((e for e in ENTRYPOINTS if e in filenames), None)
        if entrypoint is None:
            continue
        found.append(Pipeline(directory, entrypoint, readme_status(directory)))
        dirnames[:] = []
    return found


def resolve(command: str, cwd: Path | None = None) -> Path | None:
    """A path that exists is the pipeline; otherwise the name of one in this workbook."""
    path = Path(command)
    if path.exists():
        return path
    root = workbook_root(cwd)
    if root is None:
        return None
    matches = [p for p in discover(root) if p.matches(command)]
    if len(matches) > 1:
        raise MacrostratError(
            f"[item]{command}[/item] names {len(matches)} pipelines",
            details="\n".join(str(p.path.relative_to(root)) for p in matches)
            + "\nPass the path instead.",
        )
    return matches[0].path if matches else None


def command_for(path: Path, args: list[str]) -> tuple[list[str], Path | None]:
    """The subprocess to launch and the directory to launch it from.

    A `cli.py` is preferred over a `Makefile` because it can take flags; the
    Makefile path remains for the pipelines that are genuinely one line. A single
    file is run as a script from its own directory, so sibling imports resolve.
    """
    if path.is_dir():
        if (path / "cli.py").is_file():
            return ["uv", "run", "python", "cli.py", *args], path
        if (path / "Makefile").is_file():
            return ["make", "-C", str(path), *args], None
        raise MacrostratError(
            f"[item]{path}[/item] has no cli.py or Makefile",
            details="Point at a script instead, or add one.",
        )
    return ["uv", "run", "python", path.name, *args], path.parent


def child_environment() -> dict[str, str]:
    """The environment a pipeline runs in: ours, with Macrostrat's resolved into it."""
    from macrostrat.core.database import database_url_for

    child = dict(environ)
    # The launcher exports its own VIRTUAL_ENV; leaving it set makes `uv` ignore it
    # with a warning and would shadow the pipeline's interpreter in tools that honour
    # it. Running a pipeline in *its* environment is the point.
    for var in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME"):
        child.pop(var, None)
    if app.settings.env is not None:
        child["MACROSTRAT_ENV"] = app.settings.env
    try:
        child["MACROSTRAT_DATABASE_URL"] = database_url_for("macrostrat")
    except KeyError as err:
        # Not fatal: a pipeline may read from somewhere else entirely, and refusing
        # here would break the runner for the case it exists to support.
        print(f"[yellow]{err}[/yellow]")
    return child


def run_pipeline(path: Path, args: list[str]) -> int:
    cmd, cwd = command_for(path, args)
    print(f"[dim]{' '.join(cmd)}[/dim] in {env_text()}")
    return run_process(cmd, env=child_environment(), cwd=cwd).returncode


def list_pipelines(root: Path) -> None:
    pipelines = discover(root)
    if not pipelines:
        print(f"[dim]No pipelines beneath {root}[/dim]")
        return
    table = Table(title=f"Pipelines in {root.name}", title_justify="left")
    table.add_column("name", style="bold")
    table.add_column("status")
    table.add_column("path", style="dim")
    for p in pipelines:
        table.add_row(p.name, p.status or "", str(p.path.relative_to(root)))
    print(table)
