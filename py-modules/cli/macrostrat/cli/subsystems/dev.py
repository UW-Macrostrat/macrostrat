"""
Scripts to assist with running various services against different environments.
"""

from os import environ
from pathlib import Path
from subprocess import CalledProcessError, run

from typer import Argument, BadParameter, Option, Typer

from macrostrat.core.config import settings
from macrostrat.core.console import echo
from macrostrat.utils import cmd, working_directory

dev_app = Typer(help="Run services in development", no_args_is_help=True)


@dev_app.command("api-v3")
def run_api_v3():
    """Run the API v3 service."""

    v3_root = settings.srcroot / "services" / "api-v3"

    # Prepare environment
    environ["uri"] = settings.pg_database

    echo(
        f"Running [bold]API v3[/bold] service in environment [bold]{settings.env}[/bold]..."
    )

    # Print warnings
    echo(
        """
        Running [bold]API v3[/bold] locally does not currently support authentication
        because ORCID authentication requires a HTTPS callback address.
        """,
        style="warning",
    )

    # Change to the service directory
    with working_directory(v3_root):
        # Run the service
        cmd("make")


@dev_app.command("unreleased")
def unreleased(
    services: list[str] = Argument(None, help="Services to check (default: all)"),
    verbose: bool = Option(False, "--verbose", "-v", help="List the commits"),
    fetch: bool = Option(True, help="Fetch origin first"),
):
    """Summarize each service's changes since its last release tag."""
    from rich.table import Table
    from rich.text import Text

    root = settings.srcroot
    builds = _service_builds(root)
    if services:
        unknown = set(services) - set(builds)
        if unknown:
            raise BadParameter(
                f"unknown service {', '.join(unknown)}; choose from {', '.join(builds)}"
            )
        builds = {s: builds[s] for s in services}

    if fetch:
        _git(root, "fetch", "-q", "origin")

    table = Table("Service", "Released", "Tagged", "Commits", "Files", "Lines")
    commit_lists = {}
    for service, paths in builds.items():
        try:
            tag = _git(
                root,
                "describe",
                "--tags",
                "--abbrev=0",
                f"--match={service}-v[0-9]*",
                "origin/main",
            )
        except CalledProcessError:
            table.add_row(service, "[dim]none[/dim]")
            continue

        version = tag.removeprefix(f"{service}-")
        rng = f"{tag}..origin/main"
        commits = _git(root, "log", "--oneline", "--no-merges", rng, "--", *paths)
        commits = commits.splitlines()
        age = _git(root, "log", "-1", "--format=%cr", tag)
        if not commits:
            table.add_row(service, version, age, "[success]up to date[/success]")
            continue

        files = added = removed = 0
        for line in _git(root, "diff", "--numstat", rng, "--", *paths).splitlines():
            a, r, _ = line.split("\t", 2)
            files += 1
            # Binary files report "-" for both counts
            if a != "-":
                added += int(a)
                removed += int(r)
        table.add_row(
            service, version, age, str(len(commits)), str(files), f"+{added} -{removed}"
        )
        commit_lists[service] = commits

    echo(table)
    if verbose:
        for service, commits in commit_lists.items():
            echo(f"\n[bold]{service}[/bold]")
            for c in commits:
                echo(Text(f"  {c}"))


def _git(root: Path, *args: str) -> str:
    return run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _service_builds(root: Path) -> dict[str, list[str]]:
    """Map each released service to the paths that trigger its build."""
    builds = {}
    for workflow in sorted((root / ".github" / "workflows").glob("build-*.yaml")):
        service = None
        paths = []
        in_paths = False
        for line in workflow.read_text().splitlines():
            stripped = line.strip()
            if stripped == "paths:":
                # Only the first list (the push trigger)
                in_paths = not paths
            elif in_paths and stripped.startswith("- "):
                paths.append(stripped[2:].strip("'\" "))
            else:
                in_paths = False
            if stripped.startswith("service:"):
                service = stripped.removeprefix("service:").strip()
        if service:
            builds[service] = paths
    return builds
