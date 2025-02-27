# Macrostrat services

This directory contains application root directories for the various services
that make up the Macrostrat platform. Each service is a separate application
that can be run independently. Currently, this is just the API service, but
others (e.g., a task runner or tile server) may be added in the future.

Services can call code from libraries, but should not call code from other
services. For now, this is not enforced, but it may be in the future.
