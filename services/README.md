# Macrostrat services

This directory contains application root directories for the various services
that make up the Macrostrat platform: the API (`api-v3`), the tile servers
(`tileserver`, `legacy-tileserver`), the Celery `worker` and the `usage-stats`
harvester. Each service is a separate application that can be run independently,
and each is built into its own image by `.github/workflows/build-<service>.yaml`.

Services can call code from libraries, but should not call code from other
services. For now, this is not enforced, but it may be in the future.

## Releasing a service

A service's version is the one in its `pyproject.toml`. Merging a new version
into `main` releases it: the build tags the image `X.Y.Z` and creates the git tag
`<service>-vX.Y.Z` on that commit. Do not create release tags by hand.

A release pull request:

1. Sets the version in `pyproject.toml` — `X.Y.Z-beta.N` for a prerelease
   (development and staging), `X.Y.Z` for production.
2. Runs `uv lock` in the service directory, since `uv.lock` records the version.
3. For a stable version, moves the `[Unreleased]` entries of the service's
   `CHANGELOG.md` under a `## [X.Y.Z]` heading. The build fails without it.

## Status routes

The HTTP services answer `/version` (the build the image was made from, set in
`MACROSTRAT_*` environment variables by CI) and `/health` (503 when the database
does not answer). Neither is cached.
