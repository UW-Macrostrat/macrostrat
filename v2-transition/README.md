# Macrostrat system

This repository attempts to bring together many independent components of the
Macrostrat system into an environment where they can be containerized and smoothly
managed. Its goal is to provide a system for experimenting with the source code
and building production images of Macrostrat services. Ultimately, Docker should be
the preferred strategy for deploying the contents of this repository.

We'd like to enable all components here to be independently installable and, to the extent possible,
configured by environment variables.