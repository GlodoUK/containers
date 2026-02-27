#!/usr/bin/env python3
import os
import argparse
import subprocess
import logging
import sys
from pathlib import Path

from .utils import setup_logging, run_command

setup_logging()
_logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="List available Kopia snapshots (useful for finding snapshot IDs before restore)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Listing options
    list_group = parser.add_argument_group("Listing options")
    list_group.add_argument(
        "--tags",
        action="append",
        default=[],
        help="Filter by Kopia tag (format key:value, repeatable)",
    )
    list_group.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Show snapshots from all users/hosts",
    )
    list_group.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Limit number of results per source",
    )
    list_group.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output raw JSON from kopia (parseable, kopia logs go to stderr)",
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
    ]
    result = run_command(connect_cmd, check=False)
    if result.returncode != 0:
        _logger.critical("Failed to connect to Kopia repository. Aborting.")
        sys.exit(1)

    # Build snapshot list command
    list_cmd = [kopia_bin, *common_flags, "snapshot", "list"]

    if args.all:
        list_cmd.append("--all")

    for tag in args.tags:
        list_cmd.append(f"--tags={tag}")

    if args.max_results is not None:
        list_cmd.append(f"--max-results={args.max_results}")

    if args.json:
        list_cmd.append("--json")

    # Run snapshot list
    _logger.info("Listing snapshots...")
    if args.json:
        result = run_command(list_cmd, capture_output=True)
        if isinstance(result, subprocess.CompletedProcess):
            print(result.stdout, end="")
    else:
        run_command(list_cmd)

    # Disconnect from kopia
    _logger.info("Disconnecting from Kopia repository...")
    disconnect_cmd = [kopia_bin, *common_flags, "repository", "disconnect"]
    run_command(disconnect_cmd, check=False)

    sys.exit(0)


if __name__ == "__main__":
    main()
