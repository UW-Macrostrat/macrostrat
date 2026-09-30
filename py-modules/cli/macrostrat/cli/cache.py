"""
Tile cache management CLI
"""

from typer import Exit, Option, Typer, confirm

from macrostrat.core.database import get_database

cli = Typer(name="cache", help="Tile cache management")

#: How long the admin token the CLI signs for the flush is good for.
_FLUSH_TOKEN_TTL_SECONDS = 300


@cli.command(name="clear")
def clear_cache(
    yes: bool = Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    varnish: bool = Option(
        True,
        "--varnish/--no-varnish",
        help="Also flush Varnish, the cache in front of the tileserver",
    ),
):
    """Clear the tile cache: the database's, then Varnish's.

    The database cache (`tile_cache.tile`) is truncated rather than deleted from.
    DELETE leaves the space allocated to the relation for autovacuum to reclaim
    later and writes WAL in proportion to the rows removed -- on a volume that is
    already full it frees nothing while making the immediate problem worse, which
    is how the September 2026 outage deepened. TRUNCATE returns the space
    immediately and writes almost no WAL. The cost is a brief ACCESS EXCLUSIVE
    lock: in-flight tile requests block until it completes.

    Varnish is flushed second, so it cannot refill from the rows just removed.
    It goes through api-v3's admin-only `/cache/flush`, the route the website's
    cache page uses, so the same command works on every environment: the API
    knows where its Varnish is, and the CLI proves admin by signing a short-lived
    token with the environment's `token_signing_key`.
    """
    from macrostrat.core.config import settings

    db = get_database()

    tiles, size = db.run_query(
        """SELECT
            greatest(
                (SELECT reltuples FROM pg_class
                 WHERE oid = 'tile_cache.tile'::regclass),
                0
            )::bigint AS tiles,
            pg_size_pretty(pg_total_relation_size('tile_cache.tile')) AS size"""
    ).one()

    also = ""
    if varnish:
        also = f", then flush Varnish at {settings.base_url}"
    if not yes:
        confirm(
            f"Truncate tile_cache.tile (about {tiles:,} tiles, {size}){also}? "
            "Tile requests will block briefly and the cache will be cold.",
            abort=True,
        )

    db.run_query("TRUNCATE tile_cache.tile")
    db.session.commit()

    print(f"Truncated tile_cache.tile — reclaimed {size} (about {tiles:,} tiles)")

    if not varnish:
        return
    try:
        banned = flush_varnish(settings)
    except FlushError as err:
        print(f"Varnish was not flushed: {err}")
        raise Exit(1)
    print(f"Flushed Varnish ({banned})")


class FlushError(Exception):
    pass


def flush_varnish(settings) -> str:
    """Ban everything in the environment's Varnish, through api-v3.

    Returns the ban expression the API applied.
    """
    from datetime import datetime, timedelta, timezone

    import requests
    from jose import jwt

    # The local stack's certificate is signed by a local authority that only the
    # system trust store knows.
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass

    key = settings.resolve_token_signing_key()
    if not key:
        raise FlushError("this environment has no token_signing_key to sign with")

    # What api-v3's `require_admin` accepts: a session JWT with PostgREST's admin
    # role, sent in the `access_token` header as the website's cookie would be.
    expires = datetime.now(timezone.utc) + timedelta(seconds=_FLUSH_TOKEN_TTL_SECONDS)
    token = jwt.encode(
        {"sub": "macrostrat-cli", "role": "web_admin", "exp": expires},
        key,
        algorithm="HS256",
    )

    url = settings.base_url.rstrip("/") + "/api/v3/cache/flush"
    try:
        resp = requests.post(
            url, headers={"access_token": f"Bearer {token}"}, json={}, timeout=30
        )
    except requests.RequestException as err:
        raise FlushError(f"could not reach {url}: {err}")
    if resp.status_code >= 400:
        raise FlushError(f"{url} answered {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("banned", "all objects")
