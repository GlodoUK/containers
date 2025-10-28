# PostgreSQL Client Tools

These images extract the postgres client tools out of the official postgres alpine
images in order to minimise as much as possible.

This was migrated from https://github.com/GlodoUK/psql-client-tools.

## Building

To build the Dockerfile locally:
`docker build . --build-arg="POSTGRES_VERSION=16.9" --build-arg="ALPINE_VERSION=3.22"`
