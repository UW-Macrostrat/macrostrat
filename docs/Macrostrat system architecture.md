# Macrostrat system architecture

Macrostrat is a web application built atop PostGIS, with APIs in Python and NodeJS. We recently completed a migration of some legacy components from MariaDB, and we are nearing completion of a new Kubernetes-based infrastructure for the system.

## Core system

Macrostrat's core is a high-performance geospatial database engine and support geological APIs and modeling software

- PostGIS database housing maps, columns, and other information
- Containerized, Kubernetes-based infrastructure running in UW–Madison's Center for High-Throughput Computing (CHTC)
- S3 object store for managing and serving files

The control infrastructure for Macrostrat's core system, including database definitions for our PostGIS database, control scripts, and ingestion pipelines, is housed in the [`UW-Macrostrat/macrostrat`](https://github.com/UW-Macrostrat/macrostrat) GitHub repository.

## APIs

Macrostrat provides information to geological web applications (including our own apps) using public web services (APIs). These are housed in several repositories.

- [`UW-Macrostrat/macrostrat-api`](https://github.com/UW-Macrostrat/macrostrat-api): Macrostrat's production API (v2; NodeJS)
- [`UW-Macrostrat/tileserver`](https://github.com/UW-Macrostrat/tileserver): Vector and raster tile server for geologic maps (Python)
- [`UW-Macrostrat/api-v3`](https://github.com/UW-Macrostrat/api-v3): Macrostrat's development API (v3; Python)

## Web interface

Macrostrat's main web application houses interfaces for interacting with Macrostrat data. This application is housed in the [`UW-Macrostrat/web`](https://github.com/UW-Macrostrat/web) repository.

## Shared modules

We maintain shared modules that help drive the backend and frontend of our applications. Many of these are organized into monorepos:

- [`UW-Macrostrat/python-libraries`](https://github.com/UW-Macrostrat/python-libraries): Python libraries used throughout Macrostrat server and control applications, including tools for database access and data processing (published to PyPI)
- - [`UW-Macrostrat/web-components`](https://github.com/UW-Macrostrat/web-components): Shared React/Typescript user interface components and frontend utilities (published to NPM)

## Rockd

The Rockd mobile app makes heavy use of Macrostrat services for data discovery, but has its own infrastructure for social features.

- Code for the Rockd mobile app and underlying infrastructure is currently housed in a single private repository.
- Rockd's website is housed in the public [`UW-Macrostrat/rockd-website`](`UW-Macrostrat/rockd-website`) repository.
