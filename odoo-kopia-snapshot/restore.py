#!/usr/bin/env python3
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger(__name__)


def main():
    _logger.critical("Not implemented")
    sys.exit(1)


if __name__ == "__main__":
    main()
