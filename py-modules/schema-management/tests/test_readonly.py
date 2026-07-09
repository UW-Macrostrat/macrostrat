"""Tests for enforced read-only environment access (PostgreSQL)."""

from pytest import mark, raises
from sqlalchemy.exc import DBAPIError

from macrostrat.database import Database
from macrostrat.schema_management.defs import test_database_cluster
from macrostrat.schema_management.readonly import (
    as_role,
    assert_read_only,
    readonly_login,
)


@mark.docker
@mark.slow
def test_readonly_login_reads_but_cannot_write():
    with test_database_cluster(username="macrostrat_admin") as admin:
        admin.run_sql("CREATE TABLE public.thing (id int)", raise_errors=True)
        admin.run_sql("INSERT INTO public.thing (id) VALUES (1)", raise_errors=True)

        # No `web_anon` in a bare cluster; borrow only pg_read_all_data.
        with readonly_login(admin.engine.url, impersonate=()) as ro_url:
            ro = Database(ro_url)

            # Reads work.
            assert ro.run_query("SELECT count(*) FROM public.thing").scalar() == 1

            # Writes are refused by role privilege.
            with raises(DBAPIError):
                ro.run_sql(
                    "INSERT INTO public.thing (id) VALUES (2)", raise_errors=True
                )

            # And the fail-closed probe agrees (write blocked even after RESET ROLE).
            assert_read_only(ro)

            # SET ROLE within the membership closure works (for grant/RLS testing).
            with as_role(ro, "pg_read_all_data"):
                assert ro.run_query("SELECT count(*) FROM public.thing").scalar() == 1

            ro.engine.dispose()


@mark.docker
@mark.slow
def test_assert_read_only_fails_closed_on_writable_connection():
    """A writable (superuser) connection must be rejected, not silently trusted."""
    with test_database_cluster(username="macrostrat_admin") as admin:
        with raises(RuntimeError):
            assert_read_only(admin)  # RESET ROLE → superuser → probe write succeeds
