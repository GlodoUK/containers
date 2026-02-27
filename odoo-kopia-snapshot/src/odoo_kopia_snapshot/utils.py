"""Shared utilities for odoo-kopia-snapshot."""

import logging
import subprocess
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)


def setup_logging():
    """Configure root logger with a consistent format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_command(cmd, check=True, capture_output=False, text=True):
    """Run a shell command and return the CompletedProcess result.

    Returns CompletedProcess on success or when check=False.
    Raises CalledProcessError when check=True and the command fails.
    """
    try:
        return subprocess.run(
            cmd, check=check, capture_output=capture_output, text=text
        )
    except subprocess.CalledProcessError as e:
        if check:
            _logger.error(f"Command failed: {' '.join(cmd)}")
            _logger.error(f"Error: {e.stderr if capture_output else str(e)}")
            raise
        return e  # pragma: no cover – unreachable when check=False
    except Exception as e:
        _logger.error(f"An error occurred while running command {' '.join(cmd)}: {e}")
        raise


def create_sha256_file(target_file):
    """Create a .sha256 checksum sidecar for *target_file*."""
    checksum_file = f"{target_file}.sha256"
    try:
        result = subprocess.run(
            ["sha256sum", target_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        with open(checksum_file, "w") as f:
            f.write(result.stdout)
    except subprocess.CalledProcessError as e:
        _logger.critical(f"Error calculating checksum: {e.stderr}")
    except FileNotFoundError:
        _logger.critical("The 'sha256sum' command was not found...")


def verify_checksum(dump_file: Path):
    """Verify SHA256 checksum of the dump file."""
    checksum_file = Path(f"{dump_file}.sha256")
    if not checksum_file.exists():
        _logger.warning(
            f"No checksum file found at {checksum_file}, skipping verification"
        )
        return
    _logger.info(f"Verifying checksum of {dump_file}...")
    try:
        subprocess.run(
            ["sha256sum", "-c", str(checksum_file)],
            check=True,
            cwd=dump_file.parent,
        )
        _logger.info("Checksum verification passed")
    except subprocess.CalledProcessError:
        _logger.critical("Checksum verification FAILED — dump file may be corrupt")
        sys.exit(1)
