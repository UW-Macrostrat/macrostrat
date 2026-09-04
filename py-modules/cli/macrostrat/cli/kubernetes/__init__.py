"""
Functions for working with a Macrostrat instance in a Kubernetes cluster.
"""

import base64
import json
from os import environ
from subprocess import run
from typing import Optional

from rich import print
from typer import Argument, Option, Typer

from macrostrat.core import app as app_

from ...core.secrets import REDACTED, refuse_non_interactive_reveal

settings = app_.settings


def read_secret(text):
    """
    Read a secret from the Kubernetes cluster.
    """
    secret = json.loads(text)

    for k, v in secret["data"].items():
        secret["data"][k] = base64.b64decode(v).decode("utf-8")

    return secret


def _kubectl(settings, args, **kwargs):
    """
    Run a kubectl command.
    """
    namespace = getattr(settings, "kube_namespace", None)
    if namespace is None:
        raise Exception("No Kubernetes namespace specified.")

    proxy = getattr(settings, "kube_proxy", None)
    env = environ
    if proxy:
        env = {
            **env,
            "HTTPS_PROXY": proxy,
            "HTTP_PROXY": proxy,
        }
    return run(["kubectl", *args], env=env, **kwargs)


def get_secret(settings, secret_name: Optional[str], *, secret_key: str = None):
    args = []
    if secret_name is not None:
        args = [
            secret_name,
            "-o",
            "json",
        ]

    password = _kubectl(
        settings, ["get", "secrets", *args], capture_output=True, text=True
    )

    if secret_name is None:
        return password.stdout

    secret = read_secret(password.stdout)["data"]
    if secret_key is None:
        return secret
    keys = secret_key.split(".")
    for key in keys:
        secret = secret[key]
    return secret


app = Typer(no_args_is_help=True)


@app.command()
def secrets(
    secret_name: Optional[str] = Argument(None),
    *,
    key: str = Option(None),
    reveal: bool = Option(False, "--reveal", help="Show secret values in plain text"),
):
    """Get a secret from the Kubernetes cluster

    Values are redacted unless --reveal is passed, which is refused without an
    interactive terminal. This command base64-decodes every field and printed
    them verbatim, so running it once from an agent or a CI job put live
    cluster secrets into a transcript.
    """

    if secret_name is None:
        print("Available secrets:")
        print(get_secret(settings, None))
        return

    if reveal:
        refuse_non_interactive_reveal("Kubernetes secrets")

    secret = get_secret(settings, secret_name, secret_key=key)
    if not reveal:
        secret = _redact_secret(secret)
    print(json.dumps(secret, indent=4))


def _redact_secret(secret):
    """Redact the values of a fetched secret, keeping its field names.

    `get_secret` returns the Secret's `data` block with every field
    base64-decoded — so *every value is a credential* — or, with `--key`, one
    of those values on its own. Field names are useful context and are kept;
    values never are, so all of them go, at any depth.
    """
    if isinstance(secret, dict):
        return {k: _redact_secret(v) for k, v in secret.items()}
    if isinstance(secret, list):
        return [_redact_secret(v) for v in secret]
    return REDACTED
