# Macrostrat

A geological data platform for exploration, integration, and analysis (v2).

This repository represents the core of the Macrostrat system, containing its
database schema and control scripts to maintain it. As such, it provides a
"build recipe" for the open-source core of Macrostrat, which in **v2** will be
provided publicly as a runnable platform for curating geologic maps and other
datasets.

The core component packaged here is a Python application designed to control
various aspects of Macrostrat's system and supporting processes (e.g., map
caching and harmonization).

## Installation

To install the Python application that controls Macrostrat, head to the
[py-root](py-root) directory. Running `make` will install the Python
dependencies and build the application.

## Usage

Once a Macrostrat configuration file is defined, the Macrostrat command-line app
presents a broad list of management functionality for Macrostrat's system. **Subsystems**
(*in progress*) define functionality for specific aspects of the system.

This CLI is rapidly evolving so expect breakage!

Most functionality requires `docker`, and either `docker compose` or
`kubectl` (for Kubernetes) to run.

```
 Usage: macrostrat [OPTIONS] COMMAND [ARGS]...

 Macrostrat control interface
 Active environment: local

╭─ Options ──────────────────────────────────────────────────────────────────────────────────╮
│ --verbose                                             [env var: MACROSTRAT_LOCAL_VERBOSE]  │
│ --help                                                Show this message and exit.          │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────╮
│ secrets                   Get a secret from the Kubernetes cluster                         │
│ shell                     Start an IPython shell                                           │
│ env                       Set the active environment                                       │
│ install                   Install Macrostrat subsystems into the Python root.              │
│ run                       Run a command in the Macrostrat command-line context             │
│ db                        Manage the Macrostrat database                                   │
│ config                    Manage configuration                                             │
│ v1                        Macrostrat CLI v1 commands                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Subsystems ───────────────────────────────────────────────────────────────────────────────╮
│ raster              Raster data integration                                                │
│ maps                Map integration system (partial overlap with v1 commands)              │
│ tileserver          Control Macrostrat's tileserver                                        │
│ paleogeography      Manage paleogeography data                                             │
│ self                Manage the Macrostrat CLI itself                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Documentation

Documentation is a work in progress. We have starting points for:

* [Macrostrat's system architecture](docs/Macrostrat%20System%20Architecture.md)

* [Macrostrat in a Box](docs/Macrostrat%20in%20a%20Box.md), a future Docker
  Compose-based setup for running Macrostrat locally on a single host

* [The `macrostrat` command line app](cli/docs/cli-usage.md)

* [Map staging scripts](map-staging/README.md): ad-hoc scripts for scraping
  vector maps from the web and uploading to Macrostrat

Other documentation of general interest can be found in the [docs/](docs/)
directory.
