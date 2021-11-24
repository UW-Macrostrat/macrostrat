# The Macrostrat monorepo

This repository attempts to bring together many independent components of the
Macrostrat system into an environment where they can be containerized and smoothly
managed. Its goal is to provide a system for experimenting with the source code
and building production images of Macrostrat services. Ultimately, Docker should be
the preferred strategy for deploying the contents of this repository.

We'd like to enable all components here to be independently installable and, to the extent possible,
configured by environment variables.

## Rules

- The Macrostrat monorepo is a _development_ environment. We should not be running this repository in production.
  Instead, containers should be built and moved to production by moving containers. A minimal, production-specific
  configuration should be used to manage containers in that environment.
- The databases under experimentation here should never be moved to the production environment. The one-way flow of data from
  production to development servers should rarely be broken.