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
    shift  # Remove 'backup' from args and pass through
    exec python3 /app/restore.py "$@"
    ;;

  shell|sh|bash)
    echo "Starting interactive shell..."
    exec /bin/bash
    ;;

  "")
    echo "No command specified. Available commands:"
    echo "  backup  - Run backup operation"
    echo "  restore - Run restore operation"
    echo "  shell   - Start interactive shell"
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
