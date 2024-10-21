"""
Functions for working with a Macrostrat instance in a Kubernetes cluster.
"""

import base64
import json
from os import environ
from subprocess import run
from typing import Optional

from macrostrat.core import app as app_
from rich import print
from typer import Argument, Option, Typer

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
    proxy = settings.get("setup.kube_proxy", None)
    shell = getattr(proxy, "shell", None)
    if shell is not None:
        command = getattr(proxy, "command")
        # Run command in the appropriate shell and harvest environment variables
        # into the Python context
        proc = run(command, shell=True, capture_output=True, **kwargs)
        # Update the environment with the output of the command

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
def secrets(secret_name: Optional[str] = Argument(None), *, key: str = Option(None)):
    """Get a secret from the Kubernetes cluster"""

    if secret_name is None:
        print("Available secrets:")
        print(get_secret(settings, None))
        return

    print(json.dumps(get_secret(settings, secret_name, secret_key=key), indent=4))
