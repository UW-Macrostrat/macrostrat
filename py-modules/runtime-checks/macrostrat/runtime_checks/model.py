"""Declarations for the check catalog and the result model they produce."""

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Sequence
from urllib.parse import urlsplit

import httpx

Level = Literal["ok", "warn", "fail"]

#: Tiers the runner knows how to execute. Checks of any other tier are skipped.
TIERS = ("http",)


@dataclass
class Result:
    name: str
    status: Level
    detail: str = ""
    service: Optional[str] = None
    url: Optional[str] = None
    elapsed: Optional[float] = None


class Expectation:
    """A property of a response. Returns a failure message, or None."""

    def __call__(self, response: httpx.Response) -> Optional[str]:
        raise NotImplementedError


class Status(Expectation):
    def __init__(self, *codes: int):
        self.codes = codes

    def __repr__(self):
        return f"Status({', '.join(map(str, self.codes))})"

    def __call__(self, response):
        if response.status_code in self.codes:
            return None
        return f"status {response.status_code}, expected {_alternatives(self.codes)}"


@dataclass(frozen=True)
class Contains(Expectation):
    text: str

    def __call__(self, response):
        if self.text in response.text:
            return None
        return f"body lacks {self.text!r}"


@dataclass(frozen=True)
class ContentType(Expectation):
    prefix: str

    def __call__(self, response):
        actual = response.headers.get("content-type", "")
        if actual.startswith(self.prefix):
            return None
        return f"content type {actual or 'missing'}, expected {self.prefix}"


@dataclass(frozen=True)
class NonEmpty(Expectation):
    def __call__(self, response):
        if response.content:
            return None
        return "empty body"


_MISSING = object()


@dataclass(frozen=True)
class JSONPath(Expectation):
    """A path into a JSON body (`success.data[0].col_id`), optionally with a value."""

    path: str
    equals: Any = _MISSING

    def __call__(self, response):
        try:
            value = response.json()
        except json.JSONDecodeError:
            return "body is not JSON"
        for key in _path_keys(self.path):
            try:
                value = value[key]
            except (KeyError, IndexError, TypeError):
                return f"no {self.path} in body"
        if self.equals is not _MISSING and value != self.equals:
            return f"{self.path} is {value!r}, expected {self.equals!r}"
        return None


@dataclass(frozen=True)
class Redirect(Expectation):
    """A server-side redirect to the path `target`, not followed.

    `same_scheme` catches https redirected to http behind a TLS-terminating proxy.
    """

    target: str
    same_scheme: bool = True

    def __call__(self, response):
        if not response.is_redirect:
            return f"status {response.status_code}, expected a redirect"
        location = response.headers["location"]
        parts = urlsplit(location)
        if parts.path != self.target:
            return f"redirects to {location}, expected {self.target}"
        if self.same_scheme and parts.scheme not in ("", response.url.scheme):
            return f"redirects to {location}, changing scheme"
        return None


@dataclass(frozen=True)
class Check:
    """One request against a service, and what its response must satisfy.

    `path` is relative to the service's host; an absolute URL is used as is.
    """

    name: str
    service: str
    path: str
    expect: Sequence[Expectation] = field(default_factory=lambda: (Status(200),))
    severity: Level = "fail"
    tier: str = "http"
    description: str = ""

    @property
    def follow_redirects(self) -> bool:
        return not any(isinstance(e, Redirect) for e in self.expect)


def _alternatives(codes):
    return " or ".join(str(c) for c in codes)


def _path_keys(path: str):
    for part in path.split("."):
        name, *indices = part.split("[")
        if name:
            yield name
        for index in indices:
            yield int(index.rstrip("]"))
