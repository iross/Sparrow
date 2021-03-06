# Sparrow

## An interface to lab data, supported by NSF EarthCube

**Sparrow** is software for managing the geochronology data
created by a laboratory. This software has the goal of managing
analytical data for indexing and public access.

The software is designed for flexibility and extensibility, so that it can
be tailored to the needs of individual analytical labs that manage a wide
variety of data. Currently, we are testing the software with Ar and detrital
zircon geochronology data.

This is both a software implementation and a specification of the default
interface that the "Lab Data Interface" will expose.

## Principles

- Federated
- Standardized basic schema
- Standardized web-facing API
- Flexible and extensible

## Modes of access

When data leaves an analytical lab, it is integrated into publications
and archived by authors. It is also archived by the lab for long-term storage.
We intend to provide several modes of data access to ease parts of this
process.

A project-centric web user interface, managed by the
lab and possibly also the researcher. We hope to eventually
support several interactions for managing the lifecycle
of analytical data:

- Link literature references to laboratory archival data
- Manage sample metadata (locations, sample names, etc.)
- Manage data embargos and public access
- Visualize data (e.g. step-heating plots, age spectra)
- Track measurement versions (e.g. new corrections)
- Download data (for authors' own analysis and archival purposes)

On the server, direct database access and a
command line interface will allow the lab to:

- Upload new and legacy data using customized scripts
- Apply new corrections without breaking
  links to published versions or raw data
- Run global checks for data integrity
- Back up the database

A web frontend will allow users outside the lab to

- Access data directly from the lab through an API for meta-analysis
- Browse a snapshot of the lab's publicly available data, possibly
  with data visualizations.
- Pull the lab's data into other endpoints, such as the Geochron
  and Macrostrat databases.

## Place within the lab

This software is designed to run on a standard virtualized
UNIX server with a minimum of setup and intervention, and outside
of the data analysis pipeline.
It will be able to accept data from a variety of data
management pipelines through simple import scripts. Generally,
these import scripts will be run on an in-lab machine with access
to the server. Data collection, storage, and analysis tools
such as [`PyChron`](https://github.com/NMGRL/PyChron)
sit immediately prior to this system in a typical lab's data production pipeline.

## Design

We want this software to be useful to many labs, so a
strong and flexible design is crucial. **Sparrow** will have an
extensible core with well-documented interfaces for pluggable
components. Key goals from a development perspective will
be a clear, concise, **well-documented** and extensible schema,
and a reasonably small and stable code footprint for the
core functionality, with clear "hooks" for lab specific
functionality.

**Sparrow**'s technology stack consist of

- Python-based API server
  - `sqlalchemy` for database access
  - `Flask` web-application framework
- PostgreSQL database backend
  - configurable and extensible schema
  - stateless schema migrations with `migra`
- `React`-based administration interface
- Managed with `git` with separate branches for analytical
  types and individual labs.
- Software packaged primarily fro lightweight, containerized
  (e.g. Docker) instances.

Code and issues for this project are tracked on Github.

# Installation

Sparrow can be run locally or in a set of Docker
containers. The configuration stack was changed in `v0.2` (May 2019)
to be more straightforward.

Development and installation using [Docker](https://www.docker.com/)
is preferred for ease of configuration and cross-platform compatibility.
Local installation is possible, but less supported.

Clone this repository and fetch submodules:
```
git clone https://github.com/EarthCubeGeochron/Sparrow.git
cd Sparrow
git submodule update --init
```

## Development with Docker

In its containerized form, the app can be installed easily
on any Unix-y environment. This containerized
distribution strategy will allow easy deployment on any infrastructure
(local, cloud hosting, AWS/Azure, etc.).
The Docker toolchain is stable and open-source.

The only installation requirements on Unix host
systems (e.g. Linux and MacOS) are `docker`, `docker-compose`, and `zsh`.
First, [install Docker](https://docs.docker.com/install/) and
`docker-compose` using the instructions for your platform, and
make sure your user can run `docker` without root permissions (typically
`sudo usermod -aG docker ${USER}`).
If `zsh` is not present on your system, install it as well.
Installation has not yet been tested on Windows.

### The command-line interface

**Sparrow** is administered using the `sparrow` command-line
interface. This command wraps application management, database management,
`docker-compose` orchestration subcommands in a single executable, simplifying
basic management tasks. If defined, lab-specific subcommands (e.g. for import
scripts) are included as well.

To install the command-line application, symlink the `bin/sparrow` executable
from this repository to somewhere on your path
(e.g. `sudo ln -s $(pwd)/bin/sparrow /usr/local/bin`).
Typing `sparrow` will download and build containers (this will take a long time on initial run) and then show the command's help page:

```
Usage: sparrow [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  config            Print configuration of backend
  create-user       Create an authorized user for the web frontend
  create-views      Recreate views only (without building rest of schema)
  import-earthchem  Import EarthChem vocabularies
  init              Initialize database schema (non-destructive)
  serve             Run a development WSGI server
  shell             Get a Python shell within the application

Docker orchestration commands:
  compose           Alias to docker-compose that respects sparrow config
  db-await          Utility that blocks until database is ready
  db-backup         Backup database to SPARROW_BACKUP_DIR
  db-export         Export database to a binary pg_dump archive
  db-import         Import database from binary pg_dump archive
  db-migration      Generate a changeset against the optimal database schema
  db-tunnel         Tunnel database connection to local port [default: 54321]
  dev-reload        Reload web browser if app is in development mode
  down              Simple wrapper for docker-compose down
  exec              Quick shortcut to docker-compose exec
  psql              Get a psql session to the database
  up                Build containers, start, detach, and follow logs.
```

### Running Sparrow

The **Sparrow** application can be run using the command
`sparrow up`.  In all cases, the environment variable
`SPARROW_SECRET_KEY` must be set before running, but other variables
will be set to default values if not provided. Thus, a minimal working
**Sparrow** demo can be run using the following command:
```
SPARROW_SECRET_KEY="TemporaryKey" sparrow up
```

This command will spin up a database engine, frontend, backend,
and gateway service (details of each service can be found in
`docker-compose.yaml`) and automatically run the `sparrow init`
command to set up database tables.
The **Sparrow** web interface can then be accessed at `http://localhost:5002`; the API can be found at `http://localhost:5002/api`.

### Configuring the application

**Sparrow** is configured using a shell script that exports environment
variables to customize the **Sparrow** installation. An example of this script
is shown in `sparrow-config.sh.example`. While not *required* (environment
variables can be set externally), this approach is strongly preferred.

At runtime, the `sparrow` application finds a configuration file by searching
upwards from the current directory until the first file named
`sparrow-config.sh` is found. Alternatively, the location of the configuration
file can be set using the `SPARROW_CONFIG` environment variable. This will
allow the `sparrow` command to be run from anywhere on the system.

### Creating a user

On navigating to the web interface for the first time, you will not be logged
in — indeed, no user will exist! To create a user, run the `sparrow
create-user` command and follow the prompts. There should be a single row in
the `user` table after running this command. Note: the `SPARROW_SECRET_KEY`
environment variable is used to encrypt passwords, so make sure
this value is kept consistent through the lifetime of the application.

### Inspecting the running application

Several `sparrow` subcommands allow inspection of the running
**Sparrow** application:

- `sparrow psql` allows interaction with the **Sparrow** database
  using the standard `psql` management tool that ships with PostgreSQL.
- `sparrow db-tunnel` exposes the PostgreSQL database engine
  on `localhost` port `54321` (database `sparrow`, user `postgres`). This is useful for schema introspection and data management using GUI tools such as
  [Postico](https://eggerapps.at/postico/).
- `sparrow shell` creates a Python shell within the application,
  allowing inspection of the API server runtime.
- `sparrow config` prints the API server configuration.
- `sparrow compose config` prints the `docker-compose` configuration
  in use for running the containerized application.

## Local development

In certain situations, development on your local machine can be easier than
working with a containerized version of the application. However, configuration bugs will be more likely, as this setup is not tested.

You must have several
dependencies installed:

- PostgreSQL v11/PostGIS (the database system)
- Python >= 3.7
- Node.js~> 11

It is recommended that you work in a Python virtual environment.

When developing locally, the `sparrow-config.sh` file is not used, and the
frontend and backend must be configured directly. Orchestration and database management commands from the `sparrow` command-line interface
are also unavailable; these could be implemented separately from the
Docker versions of the commands if there is demand.

## Environment variables index

- `SPARROW_SECRET_KEY="very secret string"`: A secret key used for management
  of passwords. Set this in your **LOCAL** environment (it will be copied to
  the Docker runtime as needed). It is the only variable required to get up and
  running with a basic Dockerized version.
- `SPARROW_BACKEND_CONFIG="<path>"`: Location of `.cfg` files containing data.
- `SPARROW_CONFIG_JSON="<path>"`: Location of `.json` file containing frontend
  configuration. This can be manually generated, but is typically set to the
  output of `sparrow config`. It is used when the frontend and backend are on
  isolated systems (i.e. when running using Docker).

## Development vs. production

In the current beta implementation of this server, the frontend and backend server
currently both run only in development mode — changes to the code are compiled in
real time and should be available upon browser reload. This will be disabled in
the future with a `SPARROW_ENV=<development,production>` environment variable
that will default to `production` and disable development-focused features such
as live code reloading and sourcemaps for performance and security.

