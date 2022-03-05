# The Macrostrat development environment 

This environment and server configuration aims to bring together independent
components of the Macrostrat system into a testing environment to support their
containerization and ongoing management.  This is the main locus of work on the
infrastructure aspects of the **Macrostrat Version 2** effort.

## Key links

- [Tile server](/tiles)
- [API](/api)

## Goals

- Organize the source repositories for Macrostrat services, configuration, and documentation in a
  centralized place to keep their capabilities broadly in sync
- Centralize experiments towards getting Macrostrat services running under Docker containers
- Provision a centralized set of easily accessible, "in-development" Macrostrat databases that can be easily
  created from the current production version, and accessed remotely for rapid testing and development.
- Experiment with new features for specific services, such as better data pipelines, editing features, and authentication
  leading towards a more collaborative and multiscale Macrostrat
- Provide a platform ready for the incorporation of multi-node server management technologies such as
  [Kubernetes](https://kubernetes.io/) once we outgrow a single server and secure the IT staff resources
  required for such a transition.

## Rules

- The Macrostrat monorepo is a _development_ environment. We should not be running this repository in production.
  Instead, containers should be built and moved to production by moving containers. A minimal, production-specific
  configuration should be used to manage containers in that environment.
- Services and components within this system should be packaged as submodules,
  runnable as Docker containers, and independently configurable using
  environment variables. Ideally, some testing should happen locally as well as in this server environment.
- Though this is a single repository, *it is not meant to replace the versioning of each constituent module*. Services should
  remain broadly independent.
- The databases under experimentation here should never be moved to the production environment. The one-way flow of data from
  production to development servers (and then, potentially, to local copies) should rarely be broken.

## Authors

- Daven Quinn
- Casey Idzikowski