# Macrostrat testing system

The overall target of Macrostrat testing is to ensure that the database and processes
that populate it are correctly structured and robust.

Macrostrat has a multipart testing framework that can test the system in multiple ways:

- Unit tests of specific low-level functionality
- **End-to-end tests** that target an empty PostgreSQL instance, setting up the database
  and populating it with data, then running processes in a "clean room" environment
- **Conformance tests** that check expected database structure _and content_ in a populated Macrostrat database.

By default, unit tests and end-to-end tests are run automatically in GitHub Actions
on every push to the `main` branch, and on pull requests. Conformance tests
can be run manually, targeting a local or remote environment as defined in a user's `macrostrat.toml` config file.

The testing framework can be invoked using the `macrostrat test` command, which is a thin wrapper around `pytest`.

Examples:

```bash
# Run all tests (unit, end-to-end, conformance)
macrostrat test all --env development
# Run only unit and end-to-end tests
macrostrat test all --skip-env
```

## Unit tests

Unit tests are scattered throughout the codebase and generally are designed to test small units of functionality
that do not touch any database. They can have fixtures locally loaded.

## End-to-end tests

End-to-end tests are tests that require a clean database instance, which is automatically set up and
torn down via the `test_db` Pytest fixture.

These can be disabled by adding the `--skip-test-database` flag to the `macrostrat test` subcommand.
This might be useful if you want to run tests quickly, as setting up and tearing down the test database
takes a bit of time.

**Note:** for the moment, ordering of these tests is important, as some tests depend on the output of others.
We will improve this by wrapping tests in a transaction block in the future.

## Conformance tests

It is important to ensure that "live" instances of the Macrostrat database have the correct
structure and content. Tests that use the `db` fixture are _conformance tests_ that check
the content of a Macrostrat database. Right now, we also call these _Environment tests_, as they
target the specific environments (e.g, `development`, `staging`, `local`) that are defined in the
`macrostrat.toml` config file. These have several configurable options:

- `--skip-env`: Skip all tests that use the `db` fixture
  This can be useful if you are running tests in an environment that does not have access to
  a populated Macrostrat database (e.g., a CI pipeline).
- `--env ENV`: Target a specific environment defined in the `macrostrat.toml` config file.
  If not specified, the current environment is used.

## Example conformance test

```python
import pytest

# These columns are part of Macrostrat's core dataset
# and should be present in all "live" Macrostrat instances.
col_ids = {500: "Piceance Basin", 1050: "Woodstock"}

# Todo: disable this for custom macrostrat instances.
@pytest.mark.parametrize("col_id,col_name", col_ids.items())
def test_specific_column_identity(db, col_id, col_name):
    """Make sure identity is maintained for a specific column from Macrostrat's core dataset."""
    res = db.run_query(
        "SELECT col_name FROM macrostrat.cols WHERE id = :id",
        dict(id=col_id),
    ).scalar()
    assert res == col_name

```


This functionality needs several improvements, including:
- Enforce that tests use a read-only database connection, to prevent accidental changes
- Mark tests for expected success in different environments (e.g., some will only work in `development`)
- Test API endpoints, not just database content
- Rename `runtime_tests` to `conformance_tests`

