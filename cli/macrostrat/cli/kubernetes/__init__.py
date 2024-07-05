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

    op = f"mirror src/{src} src/{dst}"
    if overwrite:
        op += " --overwrite"

    if src is None and dst is None:
        print("No source or destination bucket specified.")
        op = "ls src"

    if user is None:
        raise Exception("Must specify a S3 user name.")

    cfg = get_secret(settings, "s3-user-" + user)

    script = f"""
    mc alias set src {getattr(settings, "s3_endpoint")} {cfg["access_key"]} {cfg["secret_key"]} --api s3v4
    mc {op}
    """

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

    # Redirect stderr to devnull
    # _stderr = sys.stderr
    # sys.stderr = open(devnull, "w")
    # docker = DockerClient(
    #     base_url=getattr(settings, "docker_base_url", "unix://var/run/docker.sock"),
    #     use_ssh_client=True,
    # )
    #
    # res = docker.containers.run(
    #     "minio/mc:latest",
    #     command=["-c", script],
    #     remove=True,
    #     detach=False,
    #     entrypoint="/bin/sh",
    #     stdout=True,
    #     stderr=False,
    #     tty=True,
    # )
    # print(res.decode("utf-8"))
    #
    # # Restore stderr
    # sys.stderr = _stderr

    # _kubectl(
    #     settings,
    #     [
    #         "run",
    #         "s3-mirror",
    #         "--restart=Never",
    #         "--image=docker.io/minio/mc:latest",
    #         "--rm",
    #         "--command",
    #         "--attach",
    #         "--",
    #         "echo",
    #         "Hello, world!",
    #         # "-c",
    #         # script,
    #     ],
    # )
