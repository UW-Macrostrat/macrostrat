"""Object-storage endpoints composed from plaintext topology plus named secrets.

The same treatment as :mod:`macrostrat.core.connections`, for Ceph / S3:

.. code-block:: toml

    [default.storage]
    endpoint = "https://storage.macrostrat.org"

    [production.storage]
    access_key = "op://Macrostrat Prod/ceph-app/access_key"
    secret_key = "op://Macrostrat Prod/ceph-app/secret_key"

    [production.storage.buckets]              # existing shape, unchanged
    map-staging = "map-staging-prod"

    [production.storage.admin]                # existing shape, type-dispatched
    type = "ceph-object-storage"
    access_key = "op://Macrostrat Prod/ceph-admin/access_key"
    secret_key = "op://Macrostrat Prod/ceph-admin/secret_key"

    [production.storage.endpoints]            # additional named endpoints
    access-logs   = "macrostrat-access-logs"  # bucket on the default endpoint
    rockd-backup  = { bucket = "rockd-photo-backup", access_key = "op://…" }

As with databases, a bare string is a *bucket* on the environment's default
endpoint, so an extra store costs one line; a table states only its
differences; and `[default.storage]` is inherited, so an endpoint URL shared by
every tier is written once.

Two things here are worse than the database case and drive the design:

**The admin credential is a different order of privilege.** A
``ceph-object-storage`` admin key drives ``radosgw-admin``, which can create and
delete users and buckets across the whole cluster — not merely read or write the
objects in one. It is kept a separate named endpoint precisely so that nothing
resolves it by accident, and so that a policy can gate it on its own.

**`secret_key` means two unrelated things.** ``[<env>.storage].secret_key`` is
an S3 secret access key; top-level ``secret_key`` is the JWT signing key for
api-v3 and PostgREST. They are unrelated, differently privileged, and one
character apart in a config file. :data:`TOKEN_SIGNING_KEY` exists so that the
distinction is at least named in code.
"""

import tempfile
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict

from macrostrat.utils import get_logger

from .connections import merge_tables
from .environment import DEFAULT_ENV
from .secrets import Secret, as_secret, is_secret_ref, reveal

log = get_logger(__name__)

#: TOML key holding an environment's storage configuration.
STORAGE_KEY = "storage"

#: Sub-tables of ``[<env>.storage]`` that are *not* endpoints.
BUCKETS_KEY = "buckets"
ENDPOINTS_KEY = "endpoints"

#: The reserved name of the cluster-admin endpoint, which already exists in
#: this shape and is read by the `storage` CLI subsystem.
ADMIN_ENDPOINT = "admin"

#: The name an unqualified request resolves to.
DEFAULT_ENDPOINT = "default"

#: The preferred name for the top-level token-signing key. `secret_key` is
#: kept as a synonym because every existing config uses it, but it collides
#: confusingly with `[<env>.storage].secret_key`, which is an S3 secret access
#: key — unrelated and far less privileged. Old CLIs ignore unknown keys, so
#: this can be adopted in a committed config before the CLI that prefers it.
TOKEN_SIGNING_KEY = "token_signing_key"

#: The legacy name, still honoured.
LEGACY_TOKEN_SIGNING_KEY = "secret_key"


def token_signing_key_value(settings):
    """The configured token-signing key, preferring the unambiguous name.

    Returns the raw configured value — a literal or an unresolved reference.
    Resolution is the caller's business, because this value confers more than
    any other in the config: a JWT signed with it and carrying
    `role: web_admin` is honoured by PostgREST, so holding it is equivalent to
    unrestricted database write access, with no database password and past
    every write gate.
    """
    for key in (TOKEN_SIGNING_KEY, LEGACY_TOKEN_SIGNING_KEY):
        value = getattr(settings, key, None)
        # Dynaconf resolves config keys through attribute access, so a key
        # sharing a name with a method or property on the settings class
        # resolves to *that* instead of to the configured value. Anything
        # callable is therefore not a configured key.
        if value is not None and not callable(value):
            return value
    return None


class StorageType(str, Enum):
    S3 = "s3"
    CephObjectStorage = "ceph-object-storage"


class MissingStorageCredential(RuntimeError):
    """An endpoint is missing an access key or a secret key."""


class StorageEndpoint(BaseModel):
    """One object-storage endpoint, with its credential pair unresolved."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    endpoint: str
    access_key: Union[str, Secret, None] = None
    secret_key: Union[str, Secret, None] = None
    bucket: Optional[str] = None
    type: StorageType = StorageType.S3
    region: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        """Whether this endpoint drives cluster administration."""
        return self.type == StorageType.CephObjectStorage

    @property
    def host(self) -> str:
        """The endpoint with any scheme stripped — what Minio and rgw want."""
        for prefix in ("https://", "http://"):
            if self.endpoint.startswith(prefix):
                return self.endpoint[len(prefix) :]
        return self.endpoint

    @property
    def secure(self) -> Optional[bool]:
        """TLS, or None when the endpoint states no scheme.

        None rather than a default, because guessing here is how a client
        silently ends up talking plaintext to a TLS endpoint.
        """
        if self.endpoint.startswith("https://"):
            return True
        if self.endpoint.startswith("http://"):
            return False
        return None

    def credentials(self) -> tuple:
        """``(access_key, secret_key)``, resolving both now.

        The only path to the plain values, so every call site is a disclosure
        point that can be found by grepping for this method.
        """
        missing = [
            name
            for name, value in (
                ("access_key", self.access_key),
                ("secret_key", self.secret_key),
            )
            if value is None
        ]
        if missing:
            raise MissingStorageCredential(
                f"Storage endpoint {self.endpoint} is missing {' and '.join(missing)}."
            )
        return reveal(self.access_key), reveal(self.secret_key)

    @classmethod
    def parse(cls, value: Mapping[str, Any]) -> "StorageEndpoint":
        if not hasattr(value, "get"):
            raise ValueError(
                f"[<env>.{STORAGE_KEY}] must be a table, got {type(value).__name__}"
            )
        endpoint = value.get("endpoint", None) or value.get("host", None)
        if not endpoint:
            raise ValueError(f"[<env>.{STORAGE_KEY}] needs an `endpoint`")

        declared = value.get("type", None)
        try:
            storage_type = (
                StorageType(str(declared).strip().lower())
                if declared
                else StorageType.S3
            )
        except ValueError:
            log.warning(
                "Storage endpoint %s declares unknown type=%r; treating it as %s.",
                endpoint,
                declared,
                StorageType.S3.value,
            )
            storage_type = StorageType.S3

        return cls(
            endpoint=str(endpoint),
            access_key=as_secret(value.get("access_key", None)),
            secret_key=as_secret(value.get("secret_key", None)),
            bucket=_opt_str(value.get("bucket", None)),
            type=storage_type,
            region=_opt_str(value.get("region", None)),
        )


def _opt_str(value) -> Optional[str]:
    return None if value is None else str(value)


def _base_table(settings) -> dict:
    """The environment's storage table with ``[default.storage]`` underneath."""
    inherited = None
    from_env = getattr(settings, "from_env", None)
    if callable(from_env):
        try:
            inherited = from_env(DEFAULT_ENV).get(STORAGE_KEY, None)
        except Exception:  # pragma: no cover - Dynaconf raises variously
            inherited = None
    merged = merge_tables(inherited, settings.get(STORAGE_KEY, None))
    # Sub-tables are handled separately, never as endpoint fields.
    return {
        k: v
        for k, v in merged.items()
        if k not in (BUCKETS_KEY, ENDPOINTS_KEY, ADMIN_ENDPOINT)
    }


def _sub_table(settings, key: str) -> dict:
    inherited = None
    from_env = getattr(settings, "from_env", None)
    if callable(from_env):
        try:
            table = from_env(DEFAULT_ENV).get(STORAGE_KEY, None) or {}
            inherited = dict(table).get(key, None)
        except Exception:  # pragma: no cover
            inherited = None
    current = dict(settings.get(STORAGE_KEY, None) or {}).get(key, None)
    return merge_tables(inherited, current)


def _named_endpoint(name, spec, base: dict) -> Optional[StorageEndpoint]:
    """Resolve one entry of ``[<env>.storage.endpoints]``."""
    if hasattr(spec, "items"):
        return StorageEndpoint.parse(merge_tables(base, spec))

    if not isinstance(spec, str) or not spec.strip():
        log.warning("Ignoring storage endpoint %r: expected a bucket or table.", name)
        return None

    if is_secret_ref(spec):
        log.warning(
            "Storage endpoint %r is a bare secret reference; a bucket name or a "
            "table was expected. Ignoring it.",
            name,
        )
        return None

    if not base.get("endpoint", None):
        log.warning(
            "Storage endpoint %r names bucket %r but this environment has no "
            "[%s] endpoint to inherit.",
            name,
            spec,
            STORAGE_KEY,
        )
        return None
    return StorageEndpoint.parse(merge_tables(base, {"bucket": spec}))


def endpoints_for(settings) -> Dict[str, StorageEndpoint]:
    """Every storage endpoint configured for the active environment, by name."""
    base = _base_table(settings)
    out: Dict[str, StorageEndpoint] = {}

    if base.get("endpoint", None):
        try:
            out[DEFAULT_ENDPOINT] = StorageEndpoint.parse(base)
        except ValueError as err:
            log.warning("Ignoring the [%s] table (%s).", STORAGE_KEY, err)

    admin = _sub_table(settings, ADMIN_ENDPOINT)
    if admin:
        try:
            out[ADMIN_ENDPOINT] = StorageEndpoint.parse(merge_tables(base, admin))
        except ValueError as err:
            log.warning("Ignoring [%s.%s] (%s).", STORAGE_KEY, ADMIN_ENDPOINT, err)

    for name, spec in _sub_table(settings, ENDPOINTS_KEY).items():
        if name in (DEFAULT_ENDPOINT, ADMIN_ENDPOINT):
            log.warning("Storage endpoint name %r is reserved; ignoring it.", name)
            continue
        endpoint = _named_endpoint(name, spec, base)
        if endpoint is not None:
            out[str(name)] = endpoint

    return out


def endpoint_for(settings, name: str = DEFAULT_ENDPOINT) -> Optional[StorageEndpoint]:
    """One named storage endpoint for the active environment, or None."""
    return endpoints_for(settings).get(name, None)


def buckets_for(settings) -> dict:
    """The environment's logical-name to bucket-name mapping."""
    return {str(k): str(v) for k, v in _sub_table(settings, BUCKETS_KEY).items()}


@contextmanager
def credential_file(contents: str, *, prefix: str = "macrostrat-", suffix: str = ""):
    """A short-lived 0600 file holding *contents*, shredded and removed after.

    Some tools — rclone, the Minio client — will only take credentials from a
    file, so the plaintext has to touch a disk. This keeps that window as small
    as it can be:

    - `mkstemp` creates the file 0600, so it is never briefly world-readable
      the way a `>` redirect or a default-umask write would be.
    - The contents are **truncated** before the file is unlinked. That matters
      when the file is bind-mounted into a container: the mount holds the inode
      open past the unlink, so removing the directory entry alone would leave
      the credentials readable for as long as the container runs.
    - Removal happens in a `finally`, so an exception mid-transfer does not
      leave the file behind.
    """
    fd, name = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    try:
        with open(fd, "w") as f:
            f.write(contents)
            f.flush()
        yield name
    finally:
        try:
            with open(name, "r+") as f:
                f.truncate(0)
                f.flush()
        except OSError:
            pass
        Path(name).unlink(missing_ok=True)
