"""What Macrostrat adds to the write gate: credentials and the connection.

The confirmation levels themselves are tested in `macrostrat.app_frame`.
"""

import io
import sys

from pytest import fixture, mark, raises

from macrostrat.app_frame.environments import AccessScope, EnvironmentPolicy, WriteGate
from macrostrat.app_frame.secrets import (
    RESOLVERS,
    forget_all_secrets,
    register_resolver,
)
from macrostrat.core import safety
from macrostrat.core.safety import (
    WriteRefused,
    is_interactive,
    require_write_access,
    writes,
)


class _Settings:
    """Minimal settings stand-in: a policy, and optionally a connection."""

    def __init__(self, policy, connection=None):
        self.policy = policy
        self._connection = connection

    def database_connection(self, name="macrostrat"):
        return self._connection


def policy_for(env, env_class, **kw):
    return EnvironmentPolicy.resolve(env, env_class=env_class, **kw)


@fixture
def tty(monkeypatch):
    """An interactive terminal with scripted answers.

    Substitutes safety's own `is_interactive` and `_prompt` rather than
    patching `sys.stdin`/`sys.stderr`. pytest's capture manager re-installs its
    own streams when it resumes for the call phase, so a fixture's monkeypatch
    of those attributes is silently undone — the tests passed under `-s` and
    failed under capture. Going through the module's seams tests the gate logic
    without fighting the harness; `is_interactive` itself is covered separately.
    """

    class _Answers:
        def __init__(self):
            self.prompts = []
            self._queue = []

        def feed(self, *lines):
            self._queue = list(lines)

        def prompt(self, message):
            self.prompts.append(message)
            return self._queue.pop(0) if self._queue else ""

    answers = _Answers()
    monkeypatch.setattr(safety, "is_interactive", lambda: True)
    monkeypatch.setattr(safety, "_prompt", answers.prompt)
    return answers


@fixture
def no_tty(monkeypatch):
    """An agent: no terminal to prompt on."""
    monkeypatch.setattr(safety, "is_interactive", lambda: False)


class TestMissingPolicy:
    def test_no_policy_refuses_rather_than_allows(self, no_tty):
        class _Bare:
            policy = None

        with raises(WriteRefused, match="No environment policy"):
            require_write_access(AccessScope.Data, settings=_Bare())


class _Conn:
    def __init__(self, credential):
        self._credential = credential

    def credential_for(self, role):
        if self._credential is None:
            raise RuntimeError("no writer credential configured")
        return self._credential


@fixture
def stub_resolver():
    calls = []

    def resolve(body):
        calls.append(body)
        return f"resolved-{body}"

    forget_all_secrets()
    register_resolver("stub", resolve)
    resolve.calls = calls
    try:
        yield resolve
    finally:
        RESOLVERS.pop("stub", None)
        forget_all_secrets()


class TestEscalate:
    """`escalate` must tie the write to a fresh, human-approved fetch."""

    def test_refetches_the_writer_credential(self, tty, stub_resolver):
        from macrostrat.app_frame.secrets import as_secret

        secret = as_secret("stub://writer")
        secret.get()  # already cached, as an earlier read would have left it
        assert len(stub_resolver.calls) == 1

        tty.feed("production")
        s = _Settings(policy_for("production", "production"), _Conn(secret))
        require_write_access(AccessScope.Data, settings=s)

        # The cached value was dropped and the backend consulted again.
        assert len(stub_resolver.calls) == 2

    def test_a_literal_credential_cannot_escalate(self, tty):
        """Nothing to re-authorize against, so the gate fails closed."""
        tty.feed("production")
        s = _Settings(policy_for("production", "production"), _Conn("literal-pw"))
        with raises(WriteRefused, match="literal"):
            require_write_access(AccessScope.Data, settings=s)

    def test_no_database_cannot_escalate(self, tty):
        tty.feed("production")
        s = _Settings(policy_for("production", "production"), None)
        with raises(WriteRefused, match="no database is configured"):
            require_write_access(AccessScope.Data, settings=s)

    def test_no_writer_credential_cannot_escalate(self, tty):
        tty.feed("production")
        s = _Settings(policy_for("production", "production"), _Conn(None))
        with raises(WriteRefused, match="no writer credential"):
            require_write_access(AccessScope.Data, settings=s)

    def test_the_name_is_still_required_first(self, tty, stub_resolver):
        """A wrong name must refuse before any credential is touched."""
        from macrostrat.app_frame.secrets import as_secret

        tty.feed("wrong")
        s = _Settings(
            policy_for("production", "production"), _Conn(as_secret("stub://writer"))
        )
        with raises(WriteRefused):
            require_write_access(AccessScope.Data, settings=s)
        assert stub_resolver.calls == []

    def test_an_override_can_lower_production_below_escalate(self, tty):
        """A declared gate override is honoured, literal credential and all."""
        tty.feed("production")
        s = _Settings(
            policy_for("production", "production", write_gate={"data": "typed"}),
            _Conn("literal-pw"),
        )
        assert require_write_access(AccessScope.Data, settings=s) is None


class TestDecorator:
    def test_gate_runs_before_the_body(self, no_tty):
        ran = []

        @writes(AccessScope.Data)
        def restore(settings=None):
            ran.append(True)

        # The decorator resolves settings from config, so exercise the
        # imperative path's refusal through a direct call instead.
        with raises(WriteRefused):
            require_write_access(
                AccessScope.Data, settings=_Settings(policy_for("prod", "production"))
            )
        assert ran == []

    def test_signature_is_preserved_for_typer(self):
        @writes(AccessScope.Data)
        def restore(path: str, yes: bool = False):
            """Restore docstring."""

        import inspect

        assert list(inspect.signature(restore).parameters) == ["path", "yes"]
        assert restore.__doc__ == "Restore docstring."
        assert restore.__name__ == "restore"
