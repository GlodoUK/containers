# renovate: datasource=docker depName=alpine versioning=docker
ARG ALPINE_VERSION=3.23
ARG POSTGRES_VERSION=16.9

# builder to pull *just* the client out of the PostgreSQL Docker image
FROM postgres:${POSTGRES_VERSION}-alpine${ALPINE_VERSION} AS pg_builder
ENV PG_TOOLS_DIR=/extract
RUN mkdir -p ${PG_TOOLS_DIR}/bin ${PG_TOOLS_DIR}/lib
RUN set -eux; \
  for bin in /usr/local/bin/psql /usr/local/bin/pg_dump /usr/local/bin/pg_restore /usr/local/bin/pg_isready; do \
    cp -v --parents "$bin" "${PG_TOOLS_DIR}/bin/"; \
    ldd "$bin" | awk '{print $3}' | grep -v '^(' | sort -u \
      | xargs -r -I{} cp -v --parents "{}" "${PG_TOOLS_DIR}/lib/"; \
  done && \
  strip ${PG_TOOLS_DIR}/bin/* || true

FROM alpine:${ALPINE_VERSION}
ARG KOPIA_VERSION=0.21.1
ENV KOPIA_CHECK_FOR_UPDATES=false

# Copy the correct postgresql-client version from pg_builder
COPY --from=pg_builder /extract/* /

# Install Python, Kopia, etc.
RUN apk add --no-cache \
      ca-certificates \
      curl \
      bash \
      nano \
      tzdata \
      python3 \
      tar \
    && curl -fsSL "https://github.com/kopia/kopia/releases/download/v${KOPIA_VERSION}/kopia-${KOPIA_VERSION}-linux-x64.tar.gz" \
        | tar xzf - -C /usr/local/bin --strip-components 1 \
    && rm -rf /tmp/*

# Create app directory
WORKDIR /app

# Copy scripts
COPY backup.py /app/backup.py
COPY restore.py /app/restore.py
COPY entrypoint.sh /app/entrypoint.sh

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/backup.py /app/restore.py

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default to doing nothing (requires explicit command)
CMD []
