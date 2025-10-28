# renovate: datasource=docker depName=alpine versioning=docker
ARG ALPINE_VERSION=3.22
ARG POSTGRES_VERSION=16.9

FROM postgres:${POSTGRES_VERSION}-alpine${ALPINE_VERSION} AS builder
ENV PG_TOOLS_DIR=/extract
RUN mkdir -p ${PG_TOOLS_DIR}/bin ${PG_TOOLS_DIR}/lib
RUN set -eux; \
  for bin in /usr/local/bin/psql /usr/local/bin/pg_dump /usr/local/bin/pg_restore; do \
    cp -v --parents "$bin" "${PG_TOOLS_DIR}/bin/"; \
    ldd "$bin" | awk '{print $3}' | grep -v '^(' | sort -u \
      | xargs -r -I{} cp -v --parents "{}" "${PG_TOOLS_DIR}/lib/"; \
  done && \
  strip ${PG_TOOLS_DIR}/bin/* || true

FROM alpine:${ALPINE_VERSION}
RUN apk add --no-cache bash
COPY --from=builder /extract/* /
ENTRYPOINT ["bash"]
