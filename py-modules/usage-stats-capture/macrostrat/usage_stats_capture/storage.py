"""Object-storage access for the access-log dumps.

A value object, not a config loader: callers construct `S3Params` from wherever
their configuration lives — environment variables in the service, `macrostrat.toml`
in the CLI — and hand it to the library.
"""

from pydantic import BaseModel


class S3Params(BaseModel):
    bucket: str
    endpoint: str
    access_key: str
    secret_key: str

    def get_client(self):
        from minio import Minio

        secure = self.endpoint.startswith("https://")
        if "/" not in self.endpoint:
            secure = True
        endpoint = self.endpoint.rstrip("/")
        for prefix in ["http://", "https://"]:
            endpoint = endpoint.replace(prefix, "")
        return Minio(
            endpoint=endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=secure,
        )
