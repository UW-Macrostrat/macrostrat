"""
Functions for working with a Macrostrat instance in a Kubernetes cluster.
"""
from contextlib import contextmanager
from portforward import forward
from os import environ
from subprocess import run
from typing import Optional
import base64
import json


@contextmanager
def database_tunnel(settings):
    """
    Create a tunnel to the remote database.
    """
    namespace = getattr(settings, "kube_namespace", None)
    pod = getattr(settings, "pg_database_pod", None)
    port = environ.get("PGPORT", "5432")
    if pod is None:
        raise Exception("No pod specified.")
    with forward(namespace, pod, int(port), 5432):
        yield


def read_secret(text):
    """
    Read a secret from the Kubernetes cluster.
    """
    secret = json.loads(text)

    for k, v in secret["data"].items():
        secret["data"][k] = base64.b64decode(v).decode("utf-8")

    return secret


def get_secret(settings, secret_name: Optional[str], *, secret_key: str = None):
    namespace = getattr(settings, "kube_namespace", None)
    if namespace is None:
        raise Exception("No Kubernetes namespace specified.")

    args = []
    if secret_name is not None:
        args = [
            secret_name,
            "-o",
            "json",
        ]

    password = run(["kubectl", "get", "secrets", *args], capture_output=True, text=True)

    if secret_name is None:
        return password.stdout

    secret = read_secret(password.stdout)["data"]
    if secret_key is None:
        return secret
    keys = secret_key.split(".")
    for key in keys:
        secret = secret[key]
    return secret
