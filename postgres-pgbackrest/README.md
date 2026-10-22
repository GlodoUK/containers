# postgres-pgbackrest

The official `postgres` image with [pgBackRest](https://pgbackrest.org) added, and
nothing else.

WAL archiving runs `archive_command` inside the PostgreSQL container, so pgBackRest
must be installed alongside PostgreSQL; no sidecar can stand in for it. The official
image already carries PostgreSQL's apt repository, so the pgBackRest package matches
the image's own distribution and libraries.

Nothing is configured in the image: archiving and the repository are configured at
run time, through PostgreSQL's `-c` flags and pgBackRest's `PGBACKREST_*` environment
variables (doop does this from a project's `pgbackrest:` block). Scheduled backups run
in a separate container, which must use the same pgBackRest version: the version is in
the tag and in the `systems.glo.pgbackrest.version` label.

## Versions

`pgbackrest` follows PostgreSQL's apt repository, not pgBackRest's GitHub releases, so
the pinned version is always one that can be installed.

## Building

To build the Dockerfile locally:
`docker build . --build-arg="POSTGRES_VERSION=17.10" --build-arg="PGBACKREST_VERSION=2.59.3"`
