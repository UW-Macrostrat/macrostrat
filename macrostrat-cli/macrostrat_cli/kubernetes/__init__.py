"""
Functions for working with a Macrostrat instance in a Kubernetes cluster.
"""
from contextlib import contextmanager
from portforward import forward
from os import environ
from threading import Thread


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
