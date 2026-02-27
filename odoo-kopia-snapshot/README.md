# odoo-kopia-snapshot

Kopia-based backup and restore for Odoo (PostgreSQL + filestore), designed for Kubernetes.

## Features

- **Full Odoo backup** — `pg_dump` + filestore captured in a single Kopia snapshot
- **Restore** — database, filestore, or both, with download-only mode for offline inspection
- **List snapshots** — filter by tag, limit results, optional JSON output
- **Kubernetes manifest generators** — CronJob for scheduled backups, Job for one-shot restores
- **Multi-Postgres-version images** — built against PostgreSQL 13–17
- **SHA-256 checksum verification** — database dumps are checksummed at backup and verified at restore
- **Configurable retention** — latest, hourly, daily, weekly, monthly, and annual policies
- **Read-only repository connection** — restores never mutate the repository

## Quick start

```bash
# 1. Generate a backup CronJob and apply it
generate-backup-cronjob \
  --namespace odoo-prod \
  --image ghcr.io/example/odoo-kopia-snapshot:2.0.1-pg17 \
  --filestore-pvc odoo-data \
  --secret-ref odoo-kopia-secrets \
  --backup-args '--kopia-repo-connect-params "azure --container=kopia --prefix=prod/"' \
  | kubectl apply -f -

# 2. List available snapshots
list-snapshots \
  --kopia-repo-connect-params 'azure --container=kopia --prefix=prod/'

# 3. Generate a restore Job for a specific snapshot
generate-restore-job \
  --namespace odoo-prod \
  --image ghcr.io/example/odoo-kopia-snapshot:2.0.1-pg17 \
  --filestore-pvc odoo-data \
  --secret-ref odoo-kopia-secrets \
  --snapshot abc123def \
  --restore-args '--postgres-restore --filestore-restore --kopia-repo-connect-params "azure --container=kopia --prefix=prod/"' \
  | kubectl apply -f -
```

## Commands

### `backup`

Dumps the PostgreSQL database, writes a SHA-256 checksum, and creates a Kopia snapshot of the Odoo data directory.

```bash
backup \
  --kopia-repo-connect-params 'azure --container=kopia --prefix=prod/'
```

| Flag                           | Default                         | Description                                                    |
| ------------------------------ | ------------------------------- | -------------------------------------------------------------- |
| `--kopia-repo-connect-params`  | _(required)_                    | Kopia repository connection string                             |
| `--no-postgres-backup`         | —                               | Skip the database dump                                         |
| `--no-postgres-backup-cleanup` | —                               | Keep the dump file after snapshot                              |
| `--postgres-backup-dir`        | `/var/lib/odoo/database-backup` | Ephemeral directory for the dump (must be inside `--odoo-dir`) |
| `--odoo-dir`                   | `/var/lib/odoo`                 | Root Odoo data directory to snapshot                           |
| `--kopia-hostname`             | `odoo`                          | Hostname recorded in Kopia (must be stable)                    |
| `--kopia-username`             | `odoo`                          | Username recorded in Kopia (must be stable)                    |
| `--kopia-compression`          | `s2-default`                    | Compression algorithm                                          |
| `--kopia-log-level`            | `info`                          | `error`, `warning`, `info`, or `debug`                         |
| `--no-kopia-maintenance`       | —                               | Skip the post-snapshot maintenance run                         |

**Retention flags** (applied as global policy):

| Flag             | Default |
| ---------------- | ------- |
| `--keep-latest`  | 42      |
| `--keep-hourly`  | 0       |
| `--keep-daily`   | 14      |
| `--keep-weekly`  | 8       |
| `--keep-monthly` | 6       |
| `--keep-annual`  | 2       |

### `restore`

Restores a database dump, filestore, or both from a Kopia snapshot. Connects to the repository in **read-only** mode.

```bash
restore abc123def \
  --kopia-repo-connect-params 'azure --container=kopia --prefix=prod/' \
  --postgres-restore \
  --filestore-restore
```

| Flag                           | Default           | Description                                                          |
| ------------------------------ | ----------------- | -------------------------------------------------------------------- |
| `snapshot` (positional)        | _(required)_      | Kopia snapshot ID (find with `list-snapshots`)                       |
| `--kopia-repo-connect-params`  | _(required)_      | Kopia repository connection string                                   |
| `--postgres-restore`           | off               | Opt-in: restore the database                                         |
| `--filestore-restore`          | off               | Opt-in: restore the filestore                                        |
| `--target-database`            | `$PGDATABASE`     | Restore the dump into this database name                             |
| `--source-database`            | _(auto-detected)_ | Original database name in the snapshot                               |
| `--pg-restore-args`            | `""`              | Extra flags passed to `pg_restore` (e.g. `--clean --if-exists`)      |
| `--download-only`              | off               | Download snapshot artifacts to disk without restoring                |
| `--download-path`              | —                 | Directory for downloaded artifacts (required with `--download-only`) |
| `--no-postgres-backup-cleanup` | —                 | Keep the dump file after restore                                     |

### `list-snapshots`

Lists available Kopia snapshots.

```bash
list-snapshots \
  --kopia-repo-connect-params 'azure --container=kopia --prefix=prod/' \
  --json
```

| Flag                          | Default      | Description                                      |
| ----------------------------- | ------------ | ------------------------------------------------ |
| `--kopia-repo-connect-params` | _(required)_ | Kopia repository connection string               |
| `--tags`                      | —            | Filter by tag (`key:value`, repeatable)          |
| `--all`                       | off          | Show snapshots from all users/hosts              |
| `--max-results`               | unlimited    | Limit results per source                         |
| `--json`                      | off          | Machine-readable JSON output (logs go to stderr) |

### `generate-backup-cronjob`

Emits a Kubernetes CronJob manifest to stdout.

```bash
generate-backup-cronjob \
  --namespace odoo-prod \
  --image ghcr.io/example/odoo-kopia-snapshot:2.0.1-pg17 \
  --filestore-pvc odoo-data \
  --secret-ref odoo-kopia-secrets \
  --schedule '30 2 * * *' \
  --backup-args '--kopia-repo-connect-params "azure --container=kopia --prefix=prod/"'
```

| Flag            | Default        | Description                        |
| --------------- | -------------- | ---------------------------------- |
| `--name`        | `kopia-backup` | CronJob resource name              |
| `--schedule`    | `0 0 * * *`    | Cron schedule expression           |
| `--backup-args` | `""`           | Extra arguments passed to `backup` |

### `generate-restore-job`

Emits a Kubernetes Job manifest to stdout.

```bash
generate-restore-job \
  --namespace odoo-prod \
  --image ghcr.io/example/odoo-kopia-snapshot:2.0.1-pg17 \
  --filestore-pvc odoo-data \
  --secret-ref odoo-kopia-secrets \
  --snapshot abc123def \
  --restore-args '--postgres-restore --filestore-restore --kopia-repo-connect-params "azure --container=kopia --prefix=prod/"'
```

| Flag             | Default         | Description                         |
| ---------------- | --------------- | ----------------------------------- |
| `--name`         | `kopia-restore` | Job resource name                   |
| `--snapshot`     | _(required)_    | Kopia snapshot ID                   |
| `--restore-args` | `""`            | Extra arguments passed to `restore` |

### Common Kubernetes generator flags

Both generators share these flags via `--help`:

| Flag                                              | Default      | Description                                           |
| ------------------------------------------------- | ------------ | ----------------------------------------------------- |
| `--namespace`                                     | _(required)_ | Kubernetes namespace                                  |
| `--image`                                         | _(required)_ | Container image reference                             |
| `--filestore-pvc`                                 | _(required)_ | PVC name for Odoo data                                |
| `--secret-ref`                                    | —            | Inject all keys from a Secret (repeatable)            |
| `--configmap-ref`                                 | —            | Inject all keys from a ConfigMap (repeatable)         |
| `--env`                                           | —            | Literal env var `NAME=VALUE` (repeatable)             |
| `--env-from-secret`                               | —            | Single env from Secret `NAME=SECRET:KEY` (repeatable) |
| `--env-from-configmap`                            | —            | Single env from ConfigMap `NAME=CM:KEY` (repeatable)  |
| `--memory-request` / `--memory-limit`             | `4Gi`        | Memory resources                                      |
| `--cpu-request` / `--cpu-limit`                   | `250m` / `1` | CPU resources                                         |
| `--run-as-user` / `--run-as-group` / `--fs-group` | `1000`       | Security context UIDs                                 |
| `--kopia-cache-size`                              | `25Gi`       | Ephemeral volume for Kopia cache                      |
| `--postgres-dump-size`                            | `100Gi`      | Ephemeral volume for dump files                       |

## Environment variables

| Variable         | Used by                         | Required                          | Description                                                       |
| ---------------- | ------------------------------- | --------------------------------- | ----------------------------------------------------------------- |
| `KOPIA_PASSWORD` | backup, restore, list-snapshots | Yes                               | Kopia repository password                                         |
| `PGHOST`         | backup, restore                 | Yes                               | PostgreSQL host                                                   |
| `PGPORT`         | backup, restore                 | Yes                               | PostgreSQL port                                                   |
| `PGUSER`         | backup, restore                 | Yes                               | PostgreSQL user                                                   |
| `PGPASSWORD`     | backup, restore                 | Yes                               | PostgreSQL password                                               |
| `PGDATABASE`     | backup, restore                 | Yes (backup) / Optional (restore) | Database name; restore uses it as the default `--target-database` |

## Docker

### Build arguments

| Arg                | Default  | Description                         |
| ------------------ | -------- | ----------------------------------- |
| `ALPINE_VERSION`   | `3.22`   | Alpine base image version           |
| `POSTGRES_VERSION` | `16.9`   | PostgreSQL client version to bundle |
| `KOPIA_VERSION`    | `0.22.3` | Kopia binary version                |

### Local build and shell

```bash
docker run --rm -it \
  "$(docker build -q . \
      --build-arg POSTGRES_VERSION=17 \
      --build-arg ALPINE_VERSION=3.22 \
      --build-arg KOPIA_VERSION=0.22.3)" \
  shell
```

### Running commands

The entrypoint accepts a command name as the first argument followed by any flags. Available commands: `backup`, `restore`, `list`, `generate-backup-cronjob`, `generate-restore-job`, and `shell`.

```bash
IMAGE=ghcr.io/example/odoo-kopia-snapshot:2.0.1-pg17

# List snapshots
docker run --rm \
  -e KOPIA_PASSWORD \
  "$IMAGE" list \
  --kopia-repo-connect-params 'azure --container=kopia --prefix=prod/'

# Run a backup
docker run --rm \
  -e KOPIA_PASSWORD -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
  -v odoo-data:/var/lib/odoo \
  "$IMAGE" backup \
  --kopia-repo-connect-params 'azure --container=kopia --prefix=prod/'

# Restore (download-only to a local directory)
docker run --rm \
  -e KOPIA_PASSWORD \
  -v "$PWD/restore-output:/restore" \
  "$IMAGE" restore abc123def \
  --kopia-repo-connect-params 'azure --container=kopia --prefix=prod/' \
  --download-only --download-path /restore

# Generate a manifest (no volumes or env needed)
docker run --rm "$IMAGE" generate-backup-cronjob \
  --namespace odoo-prod \
  --image "$IMAGE" \
  --filestore-pvc odoo-data \
  --secret-ref odoo-kopia-secrets \
  --backup-args '--kopia-repo-connect-params "azure --container=kopia --prefix=prod/"'
```

> **Note:** The entrypoint command for listing snapshots is `list` (not `list-snapshots`).

## Architecture note

This is a **snapshot-level** tool — each backup is a point-in-time `pg_dump` plus a filestore copy. It is not a WAL/PITR solution. For full coverage, pair it with continuous WAL archiving and periodic `pg_basebackup`.

Kopia temp/cache space must be sized to accommodate your filestore and dump, or snapshots will fail. Monitor ephemeral volume usage in your Kubernetes cluster.

## Development

```bash
uv run pytest          # run the test suite
```

- `versions.yaml` tracks the release version and the PostgreSQL/Kopia version matrix (managed by Renovate)
- To release: bump the version in both `versions.yaml` and `pyproject.toml`
