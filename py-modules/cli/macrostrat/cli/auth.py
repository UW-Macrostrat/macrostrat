"""
Delegated API tokens.

A delegated token is a credential handed to a consumer of a guarded endpoint so
they can reach it without a browser session. Only web_admins have this CLI and
the database credentials it uses, so *running these commands is the
authorization check*.

The token is a JWT signed with SECRET_KEY, so it is self-describing and
provably ours. Authority comes from the stored row, not the signature: the row
carries the scopes, and revoking a token expires that row (see `revoke-token`).

Only the token's sha256 digest is stored, so a lost token is normally reissued
rather than recovered. (The payload is just `{label, exp}`, so anyone holding
SECRET_KEY *and* the stored `expires_on` could re-derive it — but that is
already a full compromise, since the same key signs login JWTs.)

Lifetime is the only thing separating the two uses:

- The web application's own token is long-lived (`--days 730`) and ships to
  every visitor, exactly like a Mapbox public token. Its value is that it can
  be revoked, not that it is secret.
- Third-party tokens are shorter-lived and revoked individually if someone
  starts scraping.

Nothing special-cases the application's token — it is a row with a distant
expiry, so it keeps working while others are minted and revoked around it.
"""

import hashlib
import re
import sys
from datetime import datetime, timedelta, timezone
from os import environ
from typing import List, Optional

from jose import jwt
from rich import print
from rich.table import Table
from typer import Argument, Option, Typer

from macrostrat.core.database import get_database
from macrostrat.core.exc import MacrostratError

cli = Typer(name="auth", help="API tokens", no_args_is_help=True)

DELEGATED_TOKEN_TYPE = "delegated"
SCOPE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*$")
SCOPE_EXAMPLE = "rasters:emit-minerals"


def _validated_scopes(scopes: List[str]) -> Optional[list[str]]:
    """Reject malformed scopes rather than minting a token that grants nothing.

    An empty list has no inferrable type in Postgres; NULL does.
    """
    malformed = [s for s in scopes if not SCOPE_PATTERN.match(s)]
    if malformed:
        raise MacrostratError(
            f"Malformed scope: {', '.join(malformed)}",
            details=(
                "Scopes are [bold]<namespace>:<resource>[/] — a colon, not a "
                f"slash.\n  For a raster layer that is [bold]{SCOPE_EXAMPLE}[/].\n"
                "  The guarded service matches scopes as exact strings, so any "
                "other shape\n  would mint a token that authenticates and then "
                "grants nothing."
            ),
        )
    return list(scopes) or None


def _signing_key() -> tuple[str, str]:
    """SECRET_KEY and the JWT algorithm, from the environment or settings.

    The same key api-v3 signs login JWTs with — a token minted here has to be
    indistinguishable from one minted by `POST /api/v3/security/tokens`. Run
    against the environment whose key you mean: a token signed with the dev key
    is not valid in production.
    """
    from macrostrat.core.config import settings

    key = environ.get("SECRET_KEY") or settings.get("secret_key")
    if not key:
        raise MacrostratError(
            "No SECRET_KEY available",
            details=(
                "Delegated tokens are signed with the same key api-v3 uses.\n"
                "  Set SECRET_KEY in the environment, or add it to the active\n"
                "  Macrostrat environment's config."
            ),
        )
    algorithm = environ.get("JWT_ENCRYPTION_ALGORITHM") or "HS256"
    return str(key), algorithm


def sign_delegated_token(label: Optional[str], expires_on: datetime) -> str:
    """A delegated token: a JWT signed with SECRET_KEY.

    Signed rather than random so a token is self-describing and provably ours —
    decode one and read what it is for and when it lapses, with no database
    access. The signature proves origin, not authority: the stored row is what
    grants scopes, and revocation acts on that row rather than on the signature
    (a signature cannot be un-signed).

    The tile server deliberately does **not** verify this signature; it hashes
    the token and looks the row up, which it must do for revocation anyway.
    That keeps SECRET_KEY out of the tile server. The payload is `{label, exp}`
    """
    key, algorithm = _signing_key()
    return jwt.encode(
        {"label": label, "exp": expires_on},
        key,
        algorithm=algorithm,
    )


def hash_token(token: str) -> str:
    """The digest stored in `macrostrat_auth.token.token`.

    Must stay identical to `hash_token` in
    `services/api-v3/api/routes/security.py`. The API and tile server verify
    tokens minted here, so all three have to agree on the algorithm.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _user_id_for(db, sub: str) -> int:
    """Resolve an ORCID iD to a user id, or fail loudly."""
    sql = 'SELECT id FROM macrostrat_auth."user" WHERE sub = :sub'
    user_id = db.run_query(sql, {"sub": sub}).scalar()
    if user_id is None:
        raise MacrostratError(
            f"No Macrostrat user with ORCID iD {sub}",
            details="They need to sign in once before a token can be tied to them.",
        )
    return user_id


@cli.command(name="create-token")
def create_token(
    label: str = Option(
        ...,
        "--label",
        "-l",
        help="Who the token is for, e.g. 'Colorado School of Mines - EMIT'",
    ),
    scope: List[str] = Option(
        [],
        "--scope",
        "-s",
        help=(
            "Scope to grant, as <namespace>:<resource>; repeat for several. "
            f"e.g. {SCOPE_EXAMPLE}"
        ),
    ),
    days: int = Option(365, "--days", help="How long the token stays valid"),
    sub: Optional[str] = Option(
        None, "--sub", help="ORCID iD, to delegate an existing user's authority"
    ),
    created_by: Optional[str] = Option(
        None, "--created-by", help="ORCID iD of the admin issuing this token"
    ),
):
    """Create a delegated API token and print it once."""

    db = get_database()

    # Validated before anything is written, so a typo costs nothing.
    scopes = _validated_scopes(scope)

    user_id = _user_id_for(db, sub) if sub else None
    issuer_id = _user_id_for(db, created_by) if created_by else None

    expires_on = datetime.now(timezone.utc) + timedelta(days=days)
    token = sign_delegated_token(label, expires_on)

    sql = """
    INSERT INTO macrostrat_auth.token
        (token, token_type, user_id, created_by, label, scopes, expires_on)
    VALUES
        (:token, :token_type, :user_id, :created_by, :label, :scopes, :expires_on)
    RETURNING id
    """
    token_id = db.run_query(
        sql,
        {
            "token": hash_token(token),
            "token_type": DELEGATED_TOKEN_TYPE,
            "user_id": user_id,
            "created_by": issuer_id,
            "label": label,
            "scopes": scopes,
            "expires_on": expires_on,
        },
    ).scalar()
    db.session.commit()

    _report(token_id, token, label, scope, days, expires_on, sub)


def _report(token_id, token, label, scope, days, expires_on, sub):
    """Print the new token, and warn if it grants nothing.
    """

    print(f"\nCreated delegated token [bold]{token_id}[/]\n")
    print(f"  For       {label}")
    print(f"  Scopes    {', '.join(scope) if scope else '[dim]none[/]'}")
    print(f"  Expires   {expires_on:%Y-%m-%d} ({days} days)")
    if sub:
        print(f"  User      {sub}")

    print(
        "\n[yellow]Copy the token now.[/] Only its hash is stored, so it "
        "cannot be shown again.\n[dim]It is one line — select the whole thing, "
        "including anything your terminal wrapped.[/]\n"
    )
    sys.stdout.write(token + "\n")
    sys.stdout.flush()

    if not scope and not sub:
        print(
            "\n[yellow]Warning:[/] this token has no scopes and no user, "
            "so it grants nothing.\n  Pass [bold]--scope[/] (e.g. "
            "[bold]--scope rasters:emit-minerals[/]) or [bold]--sub[/]."
        )


# The token digest is never selected: it is not needed to administer a token,
# and a listing that prints it invites pasting it somewhere it can leak.
_LIST_TOKENS = """
SELECT t.id,
       t.label,
       t.token_type,
       t.scopes,
       t.created_on,
       t.expires_on,
       t.used_on,
       t.expires_on > now() AS active,
       coalesce(t.label, u.sub, '') AS issued_for,
       c.sub AS issued_by
FROM macrostrat_auth.token t
LEFT JOIN macrostrat_auth."user" u ON u.id = t.user_id
LEFT JOIN macrostrat_auth."user" c ON c.id = t.created_by
ORDER BY t.id DESC
"""


@cli.command(name="list-tokens")
def list_tokens(
    active_only: bool = Option(
        False, "--active", help="Hide tokens that have already expired"
    ),
):
    """List issued API tokens. Never shows the tokens themselves."""

    db = get_database()
    rows = list(db.run_query(_LIST_TOKENS).mappings())

    if active_only:
        rows = [r for r in rows if r["active"]]

    if not rows:
        print("No tokens." if not active_only else "No active tokens.")
        return

    table = Table(box=None, pad_edge=False)
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("For")
    table.add_column("Type")
    table.add_column("Scopes")
    table.add_column("Expires")
    table.add_column("Last used")

    for row in rows:
        status = "[green]active[/]" if row["active"] else "[dim]expired[/]"
        scopes = ", ".join(row["scopes"] or []) or "[dim]none[/]"
        used = f"{row['used_on']:%Y-%m-%d}" if row["used_on"] else "[dim]never[/]"
        table.add_row(
            str(row["id"]),
            status,
            row["issued_for"] or "[dim]—[/]",
            row["token_type"],
            scopes,
            f"{row['expires_on']:%Y-%m-%d}",
            used,
        )

    print(table)


# Revoking sets the expiry rather than deleting the row, so the record of who
# was issued survives.
_REVOKE_TOKEN = """
UPDATE macrostrat_auth.token
SET expires_on = now()
WHERE id = :token_id
  AND expires_on > now()
RETURNING id
"""
_TOKEN_EXISTS = "SELECT id FROM macrostrat_auth.token WHERE id = :token_id"


@cli.command(name="revoke-token")
def revoke_token(
    token_id: int = Argument(..., help="Token id, from `macrostrat auth list-tokens`"),
):
    """Revoke a token by expiring it. The row is kept for the record."""

    db = get_database()
    revoked = db.run_query(_REVOKE_TOKEN, {"token_id": token_id}).scalar()
    db.session.commit()

    if revoked is not None:
        print(f"Revoked token [bold]{token_id}[/].")
        print(
            "[dim]The tile server caches token lookups briefly, so this can "
            "take up to a minute to take effect.[/]"
        )
        return

    exists = db.run_query(_TOKEN_EXISTS, {"token_id": token_id}).scalar()
    if exists is None:
        raise MacrostratError(f"No token with id {token_id}")
    print(f"Token [bold]{token_id}[/] had already expired. Nothing to do.")
