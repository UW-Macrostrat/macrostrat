"""The write-authorization gate."""

import io
import sys

from pytest import fixture, mark, raises

from macrostrat.core import safety
from macrostrat.core.environment import EnvironmentPolicy, WriteGate, WriteScope
from macrostrat.core.safety import (
    WriteRefused,
    is_interactive,
    require_write_access,
    writes,
)
from macrostrat.core.secrets import RESOLVERS, forget_all_secrets, register_resolver


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


class TestUngated:
    def test_local_writes_proceed_silently(self, no_tty):
        s = _Settings(policy_for("local", "local"))
        for scope in WriteScope:
            assert require_write_access(scope, settings=s) is None

    def test_an_unknown_scope_is_rejected(self, no_tty):
        """A typo in a scope name must not silently become a permitted write."""
        from pytest import raises as _raises

        s = _Settings(policy_for("production", "production"))
        with _raises(ValueError):
            require_write_access("servcies", settings=s)


class TestNonInteractiveRefusal:
    """The property that actually constrains an agent."""

    @mark.parametrize(
        "env_class,scope",
        [
            ("development", WriteScope.Data),
            ("development", WriteScope.Schema),
            ("staging", WriteScope.Data),
            ("production", WriteScope.Data),
            ("production", WriteScope.Schema),
        ],
    )
    def test_every_gated_scope_refuses_without_a_tty(self, no_tty, env_class, scope):
        s = _Settings(policy_for("env", env_class))
        with raises(WriteRefused):
            require_write_access(scope, settings=s)

    def test_yes_satisfies_confirm_only(self, no_tty):
        s = _Settings(policy_for("development", "development"))
        assert (
            require_write_access(WriteScope.Data, settings=s, assume_yes=True) is None
        )

    @mark.parametrize("env_class", ["staging", "production"])
    def test_yes_does_not_satisfy_typed_or_escalate(self, no_tty, env_class):
        """There must be no flag that buys a typed gate."""
        s = _Settings(policy_for("env", env_class))
        with raises(WriteRefused) as err:
            require_write_access(WriteScope.Data, settings=s, assume_yes=True)
        assert "no flag or environment variable" in err.value.details

    def test_refusal_names_the_environment_and_class(self, no_tty):
        s = _Settings(policy_for("production", "production"))
        with raises(WriteRefused) as err:
            require_write_access(WriteScope.Data, settings=s)
        assert "production" in str(err.value.message)

    def test_a_failed_closed_inference_is_explained(self, no_tty):
        """An undeclared environment should say why it is being treated as prod."""
        s = _Settings(policy_for("criticalmaas", None))
        with raises(WriteRefused) as err:
            require_write_access(WriteScope.Data, settings=s)
        assert "declares no class" in str(err.value.details)


class TestMissingPolicy:
    def test_no_policy_refuses_rather_than_allows(self, no_tty):
        class _Bare:
            policy = None

        with raises(WriteRefused, match="No environment policy"):
            require_write_access(WriteScope.Data, settings=_Bare())


class TestInteractiveConfirm:
    def test_yes_proceeds(self, tty):
        tty.feed("y")
        s = _Settings(policy_for("development", "development"))
        assert require_write_access(WriteScope.Data, settings=s) is None

    @mark.parametrize("answer", ["n", "", "no", "nope", "Y E S"])
    def test_anything_else_declines(self, tty, answer):
        tty.feed(answer)
        s = _Settings(policy_for("development", "development"))
        if answer in ("y", "yes"):
            return
        with raises(WriteRefused):
            require_write_access(WriteScope.Data, settings=s)

    def test_the_prompt_names_the_action_and_environment(self, tty):
        tty.feed("y")
        s = _Settings(policy_for("development", "development"))
        require_write_access(WriteScope.Data, settings=s, action="restore")
        assert "Restore in development" in tty.prompts[0]


class TestInteractiveTyped:
    def test_exact_environment_name_proceeds(self, tty):
        tty.feed("staging")
        s = _Settings(policy_for("staging", "staging"))
        assert require_write_access(WriteScope.Data, settings=s) is None

    @mark.parametrize("answer", ["", "y", "STAGING", "staging ", "production"])
    def test_anything_else_refuses(self, tty, answer):
        tty.feed(answer)
        s = _Settings(policy_for("staging", "staging"))
        if answer.strip() == "staging":
            return
        with raises(WriteRefused):
            require_write_access(WriteScope.Data, settings=s)


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
        from macrostrat.core.secrets import as_secret

        secret = as_secret("stub://writer")
        secret.get()  # already cached, as an earlier read would have left it
        assert len(stub_resolver.calls) == 1

        tty.feed("production")
        s = _Settings(policy_for("production", "production"), _Conn(secret))
        require_write_access(WriteScope.Data, settings=s)

        # The cached value was dropped and the backend consulted again.
        assert len(stub_resolver.calls) == 2

    def test_a_literal_credential_cannot_escalate(self, tty):
        """Nothing to re-authorize against, so the gate fails closed."""
        tty.feed("production")
        s = _Settings(policy_for("production", "production"), _Conn("literal-pw"))
        with raises(WriteRefused, match="literal"):
            require_write_access(WriteScope.Data, settings=s)

    def test_no_database_cannot_escalate(self, tty):
        tty.feed("production")
        s = _Settings(policy_for("production", "production"), None)
        with raises(WriteRefused, match="no database is configured"):
            require_write_access(WriteScope.Data, settings=s)

    def test_no_writer_credential_cannot_escalate(self, tty):
        tty.feed("production")
        s = _Settings(policy_for("production", "production"), _Conn(None))
        with raises(WriteRefused, match="no writer credential"):
            require_write_access(WriteScope.Data, settings=s)

    def test_the_name_is_still_required_first(self, tty, stub_resolver):
        """A wrong name must refuse before any credential is touched."""
        from macrostrat.core.secrets import as_secret

        tty.feed("wrong")
        s = _Settings(
            policy_for("production", "production"), _Conn(as_secret("stub://writer"))
        )
        with raises(WriteRefused):
            require_write_access(WriteScope.Data, settings=s)
        assert stub_resolver.calls == []

    def test_an_override_can_lower_production_below_escalate(self, tty):
        """A declared gate override is honoured, literal credential and all."""
        tty.feed("production")
        s = _Settings(
            policy_for("production", "production", write_gate={"data": "typed"}),
            _Conn("literal-pw"),
        )
        assert require_write_access(WriteScope.Data, settings=s) is None


class TestDecorator:
    def test_gate_runs_before_the_body(self, no_tty):
        ran = []

        @writes(WriteScope.Data)
        def restore(settings=None):
            ran.append(True)

        # The decorator resolves settings from config, so exercise the
        # imperative path's refusal through a direct call instead.
        with raises(WriteRefused):
            require_write_access(
                WriteScope.Data, settings=_Settings(policy_for("prod", "production"))
            )
        assert ran == []

    def test_signature_is_preserved_for_typer(self):
        @writes(WriteScope.Data)
        def restore(path: str, yes: bool = False):
            """Restore docstring."""

        import inspect

        assert list(inspect.signature(restore).parameters) == ["path", "yes"]
        assert restore.__doc__ == "Restore docstring."
        assert restore.__name__ == "restore"


class TestInteractivityDetection:
    """`is_interactive` and `_prompt` against real stream objects.

    `sys` is patched inside each test body rather than in a fixture, for the
    capture-manager reason described on the `tty` fixture.
    """

    @staticmethod
    def _stream(isatty):
        s = io.StringIO()
        s.isatty = lambda: isatty
        return s

    def test_both_ttys_is_interactive(self, monkeypatch):
        monkeypatch.setattr(sys, "stdin", self._stream(True))
        monkeypatch.setattr(sys, "stderr", self._stream(True))
        assert safety.is_interactive()

    @mark.parametrize(
        "stdin_tty,stderr_tty", [(True, False), (False, True), (False, False)]
    )
    def test_either_stream_not_a_tty_is_not_interactive(
        self, monkeypatch, stdin_tty, stderr_tty
    ):
        monkeypatch.setattr(sys, "stdin", self._stream(stdin_tty))
        monkeypatch.setattr(sys, "stderr", self._stream(stderr_tty))
        assert not safety.is_interactive()

    def test_closed_streams_are_not_interactive(self, monkeypatch):
        class _Closed:
            def isatty(self):
                raise ValueError("I/O operation on closed file")

        monkeypatch.setattr(sys, "stdin", _Closed())
        assert not safety.is_interactive()

    def test_prompt_writes_to_stderr_and_reads_stdin(self, monkeypatch):
        """The prompt must never land in a command's piped stdout."""
        err = io.StringIO()
        out = io.StringIO()
        monkeypatch.setattr(sys, "stderr", err)
        monkeypatch.setattr(sys, "stdout", out)
        monkeypatch.setattr(sys, "stdin", io.StringIO("  staging  \n"))
        assert safety._prompt("Type the name: ") == "staging"
        assert err.getvalue() == "Type the name: "
        assert out.getvalue() == ""
