from pathlib import Path
from typing import List, Optional

from typer import Option


def check(
    service: Optional[List[str]] = Option(
        None, "--service", "-s", help="Only check these services. Repeatable."
    ),
    base_url: Optional[str] = Option(
        None, help="Check this URL instead of the environment's base_url."
    ),
    tiles_url: Optional[str] = Option(
        None, help="Check this URL instead of the environment's tiles_url."
    ),
    json: bool = Option(False, "--json", help="Print results as JSON."),
    junit: Optional[Path] = Option(None, help="Also write results as JUnit XML."),
    timeout: float = Option(10, help="Seconds to wait for each response."),
):
    """Check that a running :app_name: environment answers as its clients expect.

    Requests each route in the check catalog against the active environment.
    On the local Docker Compose stack, also checks storage credentials. Read-only.
    """
    from sys import exit

    from click import BadParameter

    from macrostrat.core import app

    from .catalog import CATALOG
    from .local import STORAGE_ROUTES, check_local_setup
    from .report import print_results, to_json, write_junit
    from .runner import SERVICE_HOSTS, run_checks

    settings = app.settings
    is_local = str(getattr(settings.backend, "value", settings.backend)) == (
        "docker-compose"
    )

    services = set(service or SERVICE_HOSTS)
    if unknown := services - set(SERVICE_HOSTS):
        known = ", ".join(SERVICE_HOSTS)
        raise BadParameter(f"unknown {', '.join(sorted(unknown))}; choose from {known}")
    if service and "local" in services and not is_local:
        raise BadParameter("the local group needs the docker-compose backend")
    if not is_local:
        services.discard("local")

    hosts = {
        "base_url": base_url or settings.base_url,
        "tiles_url": tiles_url or getattr(settings, "tiles_url", None),
    }
    checks = [c for c in [*CATALOG, *STORAGE_ROUTES] if c.service in services]
    results = run_checks(checks, hosts, timeout=timeout)
    if "local" in services:
        results += list(check_local_setup(settings))

    if json:
        print(to_json(results))
    else:
        print_results(app.console, results)
    if junit:
        write_junit(results, junit)
    if any(r.status == "fail" for r in results):
        exit(1)
