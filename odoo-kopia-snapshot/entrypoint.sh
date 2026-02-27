#!/bin/bash
set -e

# Entrypoint script for odoo-kopia-snapshot container
# Supports: backup, restore, or custom commands

COMMAND="${1:-}"

case "$COMMAND" in
  backup)
    echo "Running backup command..."
    shift  # Remove 'backup' from args and pass through
    exec python3 /app/backup.py "$@"
    ;;

  restore)
    echo "Running restore command..."
    shift  # Remove 'restore' from args and pass through
    exec python3 /app/restore.py "$@"
    ;;

  list)
    echo "Running list command..."
    shift  # Remove 'list' from args and pass through
    exec python3 /app/list.py "$@"
    ;;

  generate-backup-cronjob)
    shift
    exec python3 /app/generate_backup_cronjob.py "$@"
    ;;

  generate-restore-job)
    shift
    exec python3 /app/generate_restore_job.py "$@"
    ;;

  shell|sh|bash)
    echo "Starting interactive shell..."
    exec /bin/bash
    ;;

  "")
    echo "No command specified. Available commands:"
    echo "  backup                   - Run backup operation"
    echo "  restore                  - Run restore operation"
    echo "  list                     - List available snapshots"
    echo "  generate-backup-cronjob  - Generate a Kubernetes CronJob YAML for backups"
    echo "  generate-restore-job     - Generate a Kubernetes Job YAML for restore"
    echo "  shell                    - Start interactive shell"
    echo ""
    echo "Example: docker run odoo-kopia-backup backup --pghost=db"
    exit 0
    ;;

  *)
    # Pass through any other command directly
    echo "Executing custom command: $*"
    exec "$@"
    ;;
esac
