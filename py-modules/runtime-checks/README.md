# macrostrat.runtime_checks

Checks that a running Macrostrat environment answers as its public clients
expect: pages load, APIs answer correctly, redirects resolve. Run with
`macrostrat check` against any environment in `macrostrat.toml`.

The catalog is in `macrostrat/runtime_checks/catalog/`, one module per service.
A check names a service, a path relative to that service's host, and
expectations of the response:

```python
Check(
    "api-v2-column",
    "api-v2",
    "/api/v2/columns?col_id=17",
    [Status(200), JSONPath("success.data[0].col_id", equals=17)],
)
```

Services reach their host through the environment's `base_url`, or `tiles_url`
for the tileserver; a service whose host is unset is skipped with a warning.

```sh
macrostrat check                                   # active environment
macrostrat --env development check -s tiles
macrostrat check -s web --base-url http://localhost:3000
macrostrat check --json
macrostrat check --junit results.xml
```

On the Docker Compose backend, a `local` group also checks the stack's storage
credentials. Exits non-zero if any check fails.
