# API v3 changelog

## [Unreleased]

- `/tasks`: start, watch (Server-Sent Events), cancel and kill runs of registered
  management tasks, recorded in `tasks.run`. Admin only.
- Update callback url variable to `REDIRECT_URI`
- `/version` reports the running build; `/health` answers 503 when the database does not
