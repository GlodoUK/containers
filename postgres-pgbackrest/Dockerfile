ARG POSTGRES_VERSION=17.10

# The official image, unchanged but for pgBackRest: archive_command runs inside the
# PostgreSQL container, so pgBackRest has to be here. The official image already
# carries PostgreSQL's own apt repository, so the package matches its distribution.
FROM postgres:${POSTGRES_VERSION}
ARG PGBACKREST_VERSION=2.59.3

RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends "pgbackrest=${PGBACKREST_VERSION}-*"; \
  rm -rf /var/lib/apt/lists/*; \
  pgbackrest version | grep -qx "pgBackRest ${PGBACKREST_VERSION}"

# Configuration comes from PGBACKREST_* environment variables, not a file; the
# directories pgBackRest writes to belong to postgres.
RUN install -d -o postgres -g postgres -m 0750 \
  /var/lib/pgbackrest /var/log/pgbackrest /var/spool/pgbackrest /tmp/pgbackrest

# pgBackRest's data directory is the image's own: PGDATA moved in PostgreSQL 18's image.
ENV PGBACKREST_PG1_PATH=${PGDATA}

LABEL systems.glo.pgbackrest.version="${PGBACKREST_VERSION}"
