# odoo-kopia-snapshot

The intended use for this container is under a Kubernetes CronJob.

This should not be your soul backup process - you should also ensure that you have WAL
backups and pg basebackups to over the gaps between the snapshots.

Snapshots are very useful for long term storage.

Monitoring is assumed to be handled as part of your Kubernetes monitoring.

## Backup

- Kopia is very touchy with it's temp space. You _must_ ensure that the space that Kopia
  can see matches the limits. If it can see more, but it's restricted, it won't be smart.
- The temp/cache space must be appropriately sized for your filestore and pg_dump or the
  snapshot will fail. This needs to be actively monitored.
- The backup script assumes that the backup location is side of the backup source
  folder and that it is emphermal i.e. it does no cleanup.

### Restore

Not yet implemented.

### Releasing

- Remember to bump the `versions.yaml` dummy `v` tag and the pyproject.toml

## Building

To build and run (shell) the Dockerfile locally:
`docker run --rm -it "$(docker build -q . --build-arg POSTGRES_VERSION=17 --build-arg ALPINE_VERSION=3.22 --build-arg KOPIA_VERSION=0.17.0)" shell`
