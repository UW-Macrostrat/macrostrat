"""`macrostrat db copy` for an environment that is not on the cluster.

The cluster plugin in tiger-macrostrat-config runs the copy as a Kubernetes Job.
Here the same `pg_dump | pg_restore` runs on this machine, each tool in a
container, with the same arguments; the data passes through this machine.
"""

import asyncio
import shlex
from dataclasses import dataclass, field
from os import environ
from typing import TYPE_CHECKING

from click import ClickException
from rich import print
from sqlalchemy.engine.url import URL
from typer import Argument, Option, echo

from macrostrat.core.connections import DatabaseRole
from macrostrat.database.transfer.stream_utils import (
    print_stdout,
    print_stream_progress,
)

from ...core.secrets import REDACTED
from .utils import libpq_environment

if TYPE_CHECKING:
    from macrostrat.core.plugins import HostContext

Command = tuple[list[str], dict[str, str]]


@dataclass
class LocalCopy:
    source: URL
    destination: URL
    tables: list[str] = field(default_factory=list)
    schemas: list[str] = field(default_factory=list)
    replace: bool = False
    image: str = "postgres:15"
    docker_localhost: str = "localhost"

    def dump_args(self) -> list[str]:
        args = ["--format=custom", "--verbose"]
        for t in self.tables:
            args += ["--table", t]
        for s in self.schemas:
            args += ["--schema", s]
        return args

    def restore_args(self) -> list[str]:
        # One transaction, so a failed copy leaves the destination untouched.
        args = ["--verbose", "--single-transaction"]
        if self.replace:
            args += ["--clean", "--if-exists"]
        # Without a database, pg_restore writes SQL to stdout instead.
        return [*args, "--dbname", self.destination.database]

    def _container(self, url: URL, tool: str, args: list[str]) -> Command:
        env = libpq_environment(url, self.docker_localhost)
        # As `macrostrat.database.transfer` runs these tools.
        cmd = ["docker", "run", "-i", "--rm", "--network", "host"]
        cmd += ["--attach", "stdin", "--attach", "stdout", "--attach", "stderr"]
        cmd += ["--log-driver", "none"]
        for name in env:
            cmd += ["-e", name]
        return [*cmd, self.image, tool, *args], env

    def dump(self) -> Command:
        return self._container(self.source, "pg_dump", self.dump_args())

    def restore(self) -> Command:
        return self._container(self.destination, "pg_restore", self.restore_args())

    async def run(self) -> bool:
        """Pipe the dump into the restore; whether both succeeded."""
        (dump_cmd, dump_env), (restore_cmd, restore_env) = self.dump(), self.restore()
        dump = await asyncio.create_subprocess_exec(
            *dump_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**environ, **dump_env},
        )
        restore = await asyncio.create_subprocess_exec(
            *restore_cmd,
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**environ, **restore_env},
        )
        try:
            await asyncio.gather(
                print_stream_progress(dump.stdout, restore.stdin, prefix="Copied"),
                print_stdout(dump.stderr),
                print_stdout(restore.stderr),
            )
            return (await dump.wait(), await restore.wait()) == (0, 0)
        except asyncio.CancelledError:
            # `docker run` forwards SIGTERM, so pg_restore rolls back.
            for proc in (dump, restore):
                if proc.returncode is None:
                    proc.terminate()
                    await proc.wait()
            raise


def describe(command: Command) -> str:
    """A command and the connection it is given, without the password."""
    cmd, env = command
    shown = {k: REDACTED if k == "PGPASSWORD" else v for k, v in env.items()}
    return " ".join([*(f"{k}={v}" for k, v in shown.items()), shlex.join(cmd)])


def _url(settings, env: str, role: DatabaseRole, database: str) -> URL:
    url = settings.database_url(role)
    if url is None:
        raise ClickException(f"{env} has no database configured")
    return url.set(database=database)


def copy_command(host: "HostContext"):
    """Build `db copy` with the cluster plugin's arguments, run on this machine."""
    from macrostrat.core.database import _settings_for_env

    def copy(
        source: str = Argument(..., help="Environment to copy from"),
        table: list[str] = Option(
            [], "--table", "-t", help="Table to copy (repeatable)"
        ),
        schema: list[str] = Option(
            [], "--schema", "-n", help="Whole schema to copy (repeatable)"
        ),
        database: str = Option(
            "macrostrat", "--database", help="Database on both sides"
        ),
        replace: bool = Option(
            False, "--replace", help="Drop and recreate objects the destination has"
        ),
        timeout: int = Option(6, "--timeout", help="Hours before the copy is killed"),
        image: str = Option(None, "--image", help="Image with pg_dump and pg_restore"),
        follow: bool = Option(
            True, "--follow/--no-follow", help="Stream the copy's logs"
        ),
        dry_run: bool = Option(False, "--dry-run", help="Print the commands and stop"),
        yes: bool = Option(
            False,
            "--yes",
            "-y",
            help="Skip the confirmation prompt where one is allowed",
        ),
    ):
        """Copy tables from SOURCE into the active environment, on this machine.

        Choose the destination as for any command, with --env or `macrostrat env`.
        [cyan]pg_dump[/] and [cyan]pg_restore[/] run here in containers, so the
        data passes through this machine. The restore is one transaction: it
        fails without changes if an object already exists, unless --replace is
        given. On the cluster, the same command runs as a Kubernetes Job.
        """
        destination = host.active.name
        if source == destination:
            raise ClickException("Source and destination are the same database")
        if not table and not schema:
            raise ClickException("Name at least one --table or --schema to copy")
        if not follow:
            raise ClickException(
                f"A copy into {destination} runs in this terminal; "
                "there is no Job to follow later"
            )

        host.require_read(source, action=f"copy from {source}")
        if not dry_run:
            # Creates and may drop tables, so it is a schema write.
            host.require_write(
                "schema",
                destination,
                action=f"copy tables into {destination}",
                assume_yes=yes,
            )

        here = _settings_for_env(destination)
        if image is None:
            image = here.get("pg_database_container", "postgres:15")
        spec = LocalCopy(
            source=_url(
                _settings_for_env(source), source, DatabaseRole.Reader, database
            ),
            destination=_url(here, destination, DatabaseRole.Writer, database),
            tables=table,
            schemas=schema,
            replace=replace,
            image=image,
            docker_localhost=here.get("docker_localhost", "localhost"),
        )

        if dry_run:
            echo(f"{describe(spec.dump())} \\\n  | {describe(spec.restore())}")
            return

        try:
            ok = asyncio.run(asyncio.wait_for(spec.run(), timeout * 3600))
        except TimeoutError:
            raise ClickException(
                f"Copy stopped after {timeout} hours; the destination is unchanged"
            )
        if not ok:
            raise ClickException("Copy failed; the destination is unchanged")
        print(f"[green]Copied into {destination}[/]")

    return copy
