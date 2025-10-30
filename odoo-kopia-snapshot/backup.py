#!/usr/bin/env python3
import time
from datetime import datetime
import os
import argparse
import subprocess
import logging
import sys
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger(__name__)


def run_command(cmd, check=True, capture_output=False, text=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, check=check, capture_output=capture_output, text=text
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        if check:
            _logger.error(f"Command failed: {' '.join(cmd)}")
            _logger.error(f"Error: {e.stderr if capture_output else str(e)}")
            raise
        return False
    except Exception as e:
        _logger.error(f"An error occurred while running command {' '.join(cmd)}: {e}")
        # Raising an exception here will stop the loop unless it's handled externally
        raise


def run_postgres_backup(args) -> Path:
    postgres_backup_directory = args.postgres_backup_dir.resolve()
    postgres_backup_directory.mkdir(parents=True, exist_ok=True)

    # Check database backup directory is inside the kopia backup
    if not postgres_backup_directory.is_relative_to(args.odoo_dir.resolve()):
        _logger.critical(
            "Postgres backup directory is not inside the backup source."
            " This is an unsupported configuration."
            " The database backup path must be inside the backup source and on"
            " emphermal storage. Aborting."
        )
        sys.exit(1)

    REQUIRED_PG_ENVIRON = [
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGPASSWORD",
        "PGDATABASE",
    ]
    if not all(os.environ.get(key) for key in REQUIRED_PG_ENVIRON):
        _logger.critical(
            "Not all environment variables required for backup were set. Aborting."
        )
        sys.exit(1)

    pg_isready = False

    _logger.info("Checking PostgreSQL is ready...")
    for i in range(1, 10):
        try:
            pg_isready = run_command(["pg_isready"])
            if pg_isready:
                break
        except subprocess.CalledProcessError:
            _logger.info(
                f"PostgreSQL is not ready.. attempt {i}. Retrying in {i} seconds..."
            )
            time.sleep(i)
        except Exception:
            raise

    if not pg_isready:
        _logger.critical("Could not contact PostgreSQL")
        sys.exit(1)

    postgres_backup_file = (
        postgres_backup_directory / f"{os.environ.get('PGDATABASE')}.dump"
    )
    _logger.info(f"Starting PostgreSQL backup to {postgres_backup_file}")
    run_command(
        [
            "pg_dump",
            "--format=custom",
            "--file",
            postgres_backup_file,
            "--verbose",
            "--no-owner",
            "--compress",
            "1",
            os.environ.get("PGDATABASE"),
        ],
    )
    return postgres_backup_file


def main():
    parser = argparse.ArgumentParser(
        description="Odoo backup script using Kopia and PostgreSQL",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # PostgreSQL arguments
    pg_group = parser.add_argument_group("PostgreSQL options")
    pg_group.add_argument(
        "--postgres-backup",
        action="store_true",
        default=True,
        help="Enable PostgreSQL backup",
    )
    pg_group.add_argument(
        "--no-postgres-backup", action="store_true", help="Disable PostgreSQL backup"
    )
    pg_group.add_argument(
        "--postgres-backup-dir",
        default=Path("/var/lib/odoo/database-backup"),
        help="Emphermal storage to place backup. It *must* be within the Kopia directory",
        type=Path,
    )
    pg_group.add_argument(
        "--postgres-backup-cleanup",
        action="store_true",
        default=True,
        help="Enable PostgreSQL backup cleanup",
    )
    pg_group.add_argument(
        "--no-postgres-backup-cleanup",
        action="store_true",
        help="Disable PostgreSQL backup cleanup",
    )

    # Odoo arguments
    odoo_group = parser.add_argument_group("Odoo options")
    odoo_group.add_argument(
        "--odoo-dir",
        default=Path("/var/lib/odoo"),
        help="Source path to backup - should contain filestore, sessions, etc.",
        type=Path,
    )

    # Kopia arguments
    kopia_group = parser.add_argument_group("Kopia options")
    kopia_group.add_argument(
        "--kopia-repo-connect-params",
        required=True,
        help='Kopia repository connection parameters (e.g., "azure --container=kopia --prefix=ns/")',
    )
    kopia_group.add_argument(
        "--kopia-cache-dir",
        default="/tmp/kopia/cache",
        help="Kopia cache directory",
        type=Path,
    )
    kopia_group.add_argument(
        "--kopia-config-file",
        default="/tmp/kopia/repository.config",
        help="Kopia configuration file (ephemeral)",
        type=Path,
    )
    kopia_group.add_argument(
        "--kopia-log-level",
        default="info",
        choices=["error", "warning", "info", "debug"],
        help="Kopia log level",
    )
    kopia_group.add_argument(
        "--kopia-log-dir",
        default="/tmp/kopia/logs",
        help="Kopia log level",
        type=Path,
    )
    kopia_group.add_argument(
        "--kopia-hostname",
        default="odoo",
        help="Kopia hostname override. This must be stable between backups",
    )
    kopia_group.add_argument(
        "--kopia-username",
        default="odoo",
        help="Kopia username override. This must be stable between backups",
    )
    kopia_group.add_argument(
        "--kopia-compression", default="s2-default", help="Kopia compression algorithm"
    )
    parser.add_argument(
        "--no-kopia-maintenance", action="store_true", help="Skip Kopia maintenance run"
    )
    kopia_group.add_argument(
        "--kopia-bin",
        type=Path,
        default="/usr/local/bin/kopia",
        help="Kopia binary path",
    )

    # Kopia retention policy arguments
    policy_group = parser.add_argument_group("Kopia retention policy")
    policy_group.add_argument(
        "--keep-latest", type=int, default=42, help="Number of latest snapshots to keep"
    )
    policy_group.add_argument(
        "--keep-hourly", type=int, default=0, help="Number of hourly snapshots to keep"
    )
    policy_group.add_argument(
        "--keep-daily", type=int, default=14, help="Number of daily snapshots to keep"
    )
    policy_group.add_argument(
        "--keep-weekly", type=int, default=8, help="Number of weekly snapshots to keep"
    )
    policy_group.add_argument(
        "--keep-monthly",
        type=int,
        default=6,
        help="Number of monthly snapshots to keep",
    )
    policy_group.add_argument(
        "--keep-annual", type=int, default=2, help="Number of annual snapshots to keep"
    )

    args = parser.parse_args()

    # Handle --no-postgres-backup flag
    if args.no_postgres_backup:
        args.postgres_backup = False

    if args.no_postgres_backup_cleanup:
        args.postgres_backup_cleanup = False

    postgres_dump_to_remove = False
    if args.postgres_backup:
        postgres_dump_to_remove = run_postgres_backup(args)

    # Ensure directories exist
    Path(args.kopia_config_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.kopia_cache_dir).mkdir(parents=True, exist_ok=True)
    Path(args.kopia_log_dir).mkdir(parents=True, exist_ok=True)

    kopia_bin = f"{args.kopia_bin}"

    # Check KOPIA_PASSWORD from environment
    if not os.environ.get("KOPIA_PASSWORD"):
        os.environ["KOPIA_PASSWORD"] = "static-passw0rd"
        _logger.warning(
            "KOPIA_PASSWORD environment variable not set. Using insecure default matching velero's old defaults..."
        )

    common_flags = [
        f"--config-file={args.kopia_config_file}",
        f"--log-level={args.kopia_log_level}",
        f"--log-dir={args.kopia_log_dir}",
        f"--file-log-level={args.kopia_log_level}",
        "--no-progress",
    ]

    overrides = [
        f"--override-hostname={args.kopia_hostname}",
        f"--override-username={args.kopia_username}",
    ]

    _logger.info(
        "Attempting to connect to Kopia repository (using ephemeral config)..."
    )
    connect_cmd = [
        kopia_bin,
        *common_flags,
        "repository",
        "connect",
        f"--cache-directory={args.kopia_cache_dir}",
        *args.kopia_repo_connect_params.split(),
        *overrides,
    ]
    if not run_command(connect_cmd, check=False):
        _logger.info(
            "Failed to connect to Kopia repository or repository not initialized. Attempting to create..."
        )
        create_cmd = [
            kopia_bin,
            *common_flags,
            "repository",
            "create",
            f"--cache-directory={args.kopia_cache_dir}",
            *args.kopia_repo_connect_params.split(),
            *overrides,
            "--description=Kopia repository for Kubernetes CronJob (ephemeral config)",
        ]
        run_command(create_cmd)

    # Set policies
    _logger.info("Setting Kopia retention policies")
    policy_global_cmd = [
        kopia_bin,
        *common_flags,
        "policy",
        "set",
        "--global",
        f"--compression={args.kopia_compression}",
        f"--keep-latest={args.keep_latest}",
        f"--keep-hourly={args.keep_hourly}",
        f"--keep-daily={args.keep_daily}",
        f"--keep-weekly={args.keep_weekly}",
        f"--keep-monthly={args.keep_monthly}",
        f"--keep-annual={args.keep_annual}",
        "--add-ignore=/sessions/*",
        f"--add-ignore={args.odoo_dir / 'sessions' / '*'}",
        "--ignore-file-errors=true",
    ]
    run_command(policy_global_cmd)

    # Set no compression for database backups (already compressed SQL)
    policy_db_cmd = [
        kopia_bin,
        *common_flags,
        "policy",
        "set",
        "--compression=none",
        f"{args.postgres_backup_dir.resolve()}",
    ]
    run_command(policy_db_cmd)

    _logger.info(f"Creating snapshot for source: {args.odoo_dir}...")
    snapshot_desc = (
        f"Kubernetes Snapshot {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    snapshot_cmd = [
        kopia_bin,
        *common_flags,
        "snapshot",
        "create",
        f"{args.odoo_dir}",
        f"--description={snapshot_desc}",
    ]
    run_command(snapshot_cmd)

    if not args.no_kopia_maintenance:
        maintenance_cmd = [
            kopia_bin,
            *common_flags,
            "maintenance",
            "run",
            "--full",
        ]
        run_command(maintenance_cmd)
    else:
        _logger.info("Skipping Kopia maintenance (--no-maintenance)")

    # Content stats
    _logger.info("Kopia content stats")
    stats_cmd = [kopia_bin, *common_flags, "content", "stats"]
    run_command(stats_cmd)

    _logger.info("Disconnecting from Kopia repository...")
    disconnect_cmd = [kopia_bin, *common_flags, "repository", "disconnect"]
    run_command(disconnect_cmd)

    if (
        args.postgres_backup_cleanup
        and postgres_dump_to_remove
        and postgres_dump_to_remove.is_file()
    ):
        _logger.info(f"Cleanup of postgres dump file {postgres_dump_to_remove}")
        postgres_dump_to_remove.unlink()

    _logger.info("Backup finished successfully.")

    sys.exit(0)


if __name__ == "__main__":
    main()
