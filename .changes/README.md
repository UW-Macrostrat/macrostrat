# Change fragments

Each file here records a pending change to a service in `services/`, to be
applied at release time. Add one in the same pull request as the change:

```bash
uv run mono changeset
```

A fragment names the services it affects, by directory, and how far each should
move, followed by the changelog entry:

```markdown
---
tileserver: minor
---

- `/map/{slug}` accepts a `style` parameter
```

Levels are `patch`, `minor` and `major`.

To release, apply the fragments on a release branch:

- `uv run mono version --pre` makes prereleases (`3.3.0-beta.1`), which reach
  development and staging. Their entries collect under `## [Unreleased]`.
- `uv run mono version` makes stable versions, which reach production too.
  `-p <service>` limits a run to that service, and releases a service at a
  prerelease as stable.

Merging the release branch releases: each build tags `<service>-vX.Y.Z`.
`uv run mono status` shows the plan without changing anything. Configuration
is `[tool.mono]` in the root `pyproject.toml`.
