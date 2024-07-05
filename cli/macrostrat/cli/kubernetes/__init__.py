"""
Functions for working with a Macrostrat instance in a Kubernetes cluster.
"""

import base64
import json
from os import environ
from subprocess import run
from typing import Optional


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


app = Typer()


@app.command()
def secrets(secret_name: Optional[str] = Argument(None), *, key: str = Option(None)):
    """Get a secret from the Kubernetes cluster"""

    if secret_name is None:
        print("Available secrets:")
        print(get_secret(settings, None))
        return

    print(json.dumps(get_secret(settings, secret_name, secret_key=key), indent=4))


@app.command()
def s3_users():
    """
    List available S3 users.
    """
    res = _kubectl(
        settings,
        ["get", "secrets", "-o", "jsonpath={.items[*].metadata.name}"],
        capture_output=True,
        text=True,
    )
    prefix = "s3-user-"
    print(
        [r.replace(prefix, "") for r in res.stdout.split(" ") if r.startswith(prefix)]
    )


@app.command()
def mirror_bucket(
    src: Optional[str] = Argument(None),
    dst: Optional[str] = Argument(None),
    user=None,
    overwrite=False,
):
    """
    Mirror two S3 buckets using a worker on the Kubernetes cluster.
    """
    # Build and run a Docker container with mc

    op = None
    script = ""

    buckets = []
    for bucket, destination in zip([src, dst], ["source", "destination"]):
        if bucket is None:
            raise Exception(f"No {destination} bucket specified.")

        user = None
        if ":" in bucket:
            # We have a username and bucket name
            user, bucket = bucket.split(":")

        if user is None:
            user = getattr(settings, "s3_user", None)

        if user is None:
            raise Exception(f"No S3 user specified for {destination}.")

        cfg = get_secret(settings, "s3-user-" + user)
        if cfg is None:
            raise Exception(f"No secret found for S3 user {user}.")

        access_key = cfg["access_key"]
        secret_key = cfg["secret_key"]
        endpoint = getattr(settings, "s3_endpoint")

        script += f"mc alias set {destination} {endpoint} {access_key} {secret_key} --api s3v4\n"
        buckets.append(f"{destination}/{bucket}/")

    script += f"mc mb " + buckets[1] + "\n"
    script += f"mc mirror " + " ".join(buckets)
    if overwrite:
        script += " --overwrite"

    print(script)

    run(
        [
            "docker",
            "run",
            "--rm",
            "-t",
            "--entrypoint=/bin/sh",
            "minio/mc:latest",
            "-c",
            script,
        ],
        env={
            "DOCKER_HOST": getattr(
                settings, "docker_base_url", "unix://var/run/docker.sock"
            ),
            **environ,
        },
    )
