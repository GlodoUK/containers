#!/usr/bin/env python3
import time
import os
import argparse
import subprocess
import logging
import shlex
import sys
from pathlib import Path

from .utils import setup_logging, run_command, verify_checksum

setup_logging()
_logger = logging.getLogger(__name__)


def detect_source_database(backup_dir: Path) -> str:
    """Auto-detect source database name from .dump filename in backup dir."""
    dump_files = list(backup_dir.glob("*.dump"))
    if len(dump_files) == 0:
        _logger.critical(f"No .dump files found in {backup_dir}")
        sys.exit(1)
    if len(dump_files) > 1:
        _logger.critical(
            f"Multiple .dump files found in {backup_dir}: {dump_files}."
            " Use --source-database to specify which one."
        )
        sys.exit(1)
    return dump_files[0].stem


def main():
    parser = argparse.ArgumentParser(
        description="Odoo restore script using Kopia and PostgreSQL",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Positional
    parser.add_argument(
        "snapshot",
        help="Kopia snapshot ID to restore from (use 'list' command to find available IDs)",
    )

    # PostgreSQL arguments
    pg_group = parser.add_argument_group("PostgreSQL options")
    pg_group.add_argument(
        "--postgres-restore",
        action="store_true",
        default=False,
        help="Enable PostgreSQL restore (opt-in)",
    )
    pg_group.add_argument(
        "--no-postgres-restore",
        action="store_true",
        help="Disable PostgreSQL restore",
    )
    pg_group.add_argument(
        "--postgres-backup-dir",
        default=Path("/var/lib/odoo/database-backup"),
        help="Local directory to restore the dump file into",
        type=Path,
    )
    pg_group.add_argument(
        "--pg-restore-args",
        default="",
        help='Extra arguments for pg_restore (e.g. "--clean --if-exists")',
    )
    pg_group.add_argument(
        "--target-database",
        default=None,
        help="Restore database as this name (defaults to PGDATABASE env var)",
    )
    pg_group.add_argument(
        "--source-database",
        default=None,
        help="Original database name in the snapshot (auto-detected from dump filename if not provided)",
    )
    pg_group.add_argument(
        "--postgres-backup-cleanup",
        action="store_true",
        default=True,
        help="Clean up dump file after restore",
    )
    pg_group.add_argument(
        "--no-postgres-backup-cleanup",
        action="store_true",
        help="Keep dump file after restore",
    )

    # Download-only mode
    parser.add_argument(
        "--download-only",
        action="store_true",
        default=False,
        help="Download snapshot data to disk without restoring (skips pg_restore and cleanup)",
    )
    parser.add_argument(
        "--download-path",
        type=Path,
        default=None,
        help="Directory to download snapshot artifacts into (required with --download-only)",
    )

    # Filestore arguments
    fs_group = parser.add_argument_group("Filestore options")
    fs_group.add_argument(
        "--filestore-restore",
        action="store_true",
        default=False,
        help="Enable filestore restore (opt-in)",
    )
    fs_group.add_argument(
        "--no-filestore-restore",
        action="store_true",
        help="Disable filestore restore",
    )
    fs_group.add_argument(
        "--odoo-dir",
        default=Path("/var/lib/odoo"),
        help="Base path for Odoo data (filestore lives under this)",
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
        help="Kopia log directory",
        type=Path,
    )
    kopia_group.add_argument(
        "--kopia-hostname",
        default="odoo",
        help="Kopia hostname override",
    )
    kopia_group.add_argument(
        "--kopia-username",
        default="odoo",
        help="Kopia username override",
    )
    kopia_group.add_argument(
        "--kopia-bin",
        type=Path,
        default="/usr/local/bin/kopia",
        help="Kopia binary path",
    )

    args = parser.parse_args()

    # Handle --no-* flags
    if args.no_postgres_restore:
        args.postgres_restore = False
    if args.no_postgres_backup_cleanup:
        args.postgres_backup_cleanup = False
    if args.no_filestore_restore:
        args.filestore_restore = False
    if args.download_only:
        args.postgres_backup_cleanup = False
        if not args.download_path:
            parser.error("--download-path is required when using --download-only")
        # Override restore paths to point at the download directory
        args.postgres_backup_dir = args.download_path
        args.odoo_dir = args.download_path

    # Resolve target database
    target_database = args.target_database or os.environ.get("PGDATABASE")

    if args.postgres_restore and not args.download_only and not target_database:
        _logger.critical(
            "No target database specified. Use --target-database or set PGDATABASE."
        )
        sys.exit(1)

    if args.postgres_restore and not args.download_only:
        REQUIRED_PG_ENVIRON = ["PGHOST", "PGPORT", "PGUSER", "PGPASSWORD"]
        if not all(os.environ.get(key) for key in REQUIRED_PG_ENVIRON):
            _logger.critical(
                "Not all PostgreSQL environment variables are set"
                " (PGHOST, PGPORT, PGUSER, PGPASSWORD). Aborting."
            )
            sys.exit(1)

    # Ensure kopia directories exist
    Path(args.kopia_config_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.kopia_cache_dir).mkdir(parents=True, exist_ok=True)
    Path(args.kopia_log_dir).mkdir(parents=True, exist_ok=True)

    kopia_bin = f"{args.kopia_bin}"

    # Check KOPIA_PASSWORD from environment
    if not os.environ.get("KOPIA_PASSWORD"):
        os.environ["KOPIA_PASSWORD"] = "static-passw0rd"
        _logger.warning(
            "KOPIA_PASSWORD environment variable not set."
            " Using insecure default matching velero's old defaults..."
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

    # Connect to kopia repository
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
        "--readonly",
    ]
    if run_command(connect_cmd, check=False).returncode != 0:
        _logger.critical("Failed to connect to Kopia repository. Aborting.")
        sys.exit(1)

    snapshot = args.snapshot

    # Restore database dump from snapshot
    if args.postgres_restore:
        postgres_backup_dir = args.postgres_backup_dir.resolve()
        postgres_backup_dir.mkdir(parents=True, exist_ok=True)

        _logger.info(f"Restoring database dump from snapshot {snapshot}...")
        restore_db_cmd = [
            kopia_bin,
            *common_flags,
            "snapshot",
            "restore",
            f"{snapshot}/database-backup",
            str(postgres_backup_dir),
        ]
        run_command(restore_db_cmd)

        # Auto-detect or use provided source database
        source_database = args.source_database or detect_source_database(
            postgres_backup_dir
        )
        _logger.info(f"Source database: {source_database}")

        dump_file = postgres_backup_dir / f"{source_database}.dump"
        if not dump_file.exists():
            _logger.critical(f"Expected dump file not found: {dump_file}")
            sys.exit(1)

        # Verify checksum
        verify_checksum(dump_file)

        if not args.download_only:
            # Wait for PostgreSQL
            _logger.info("Checking PostgreSQL is ready...")
            pg_isready = False
            for i in range(1, 10):
                try:
                    result = run_command(["pg_isready"])
                    if result.returncode == 0:
                        pg_isready = True
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

            # Run pg_restore
            _logger.info(f"Restoring database dump to {target_database}...")
            pg_restore_cmd = [
                "pg_restore",
                f"--dbname={target_database}",
                "--verbose",
                "--no-owner",
            ]
            if args.pg_restore_args:
                pg_restore_cmd.extend(shlex.split(args.pg_restore_args))
            pg_restore_cmd.append(str(dump_file))
            run_command(pg_restore_cmd)

            # Clean up dump files
            if args.postgres_backup_cleanup:
                _logger.info(f"Cleaning up dump file {dump_file}")
                dump_file.unlink(missing_ok=True)
                checksum_file = Path(f"{dump_file}.sha256")
                checksum_file.unlink(missing_ok=True)
        else:
            _logger.info(f"Download-only mode: dump file available at {dump_file}")
    else:
        # Even without postgres restore, we may need source_database for filestore
        source_database = args.source_database

    # Restore filestore
    if args.filestore_restore:
        if not source_database:
            _logger.critical(
                "Cannot restore filestore without knowing the source database name."
                " Use --source-database or enable --postgres-restore for auto-detection."
            )
            sys.exit(1)

        filestore_target = target_database or source_database
        odoo_dir = args.odoo_dir.resolve()
        target_path = odoo_dir / "filestore" / filestore_target

        _logger.info(
            f"Restoring filestore from snapshot {snapshot}"
            f" (source: {source_database}, target: {filestore_target})..."
        )
        target_path.mkdir(parents=True, exist_ok=True)
        restore_fs_cmd = [
            kopia_bin,
            *common_flags,
            "snapshot",
            "restore",
            f"{snapshot}/filestore/{source_database}",
            str(target_path),
        ]
        run_command(restore_fs_cmd)
        _logger.info("Filestore restore complete")

    # Disconnect from kopia
    _logger.info("Disconnecting from Kopia repository...")
    disconnect_cmd = [kopia_bin, *common_flags, "repository", "disconnect"]
    run_command(disconnect_cmd)

    _logger.info("Restore finished successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
