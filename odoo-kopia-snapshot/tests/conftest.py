"""Shared test fixtures."""

from types import SimpleNamespace

import pytest


@pytest.fixture()
def make_args():
    """Return a factory that builds a SimpleNamespace with sane defaults.

    Override any attribute by passing keyword arguments.
    """

    def _make_args(**overrides):
        defaults = {
            "namespace": "test-ns",
            "image": "ghcr.io/example/odoo-kopia-snapshot:latest",
            "secret_ref": [],
            "configmap_ref": [],
            "env_literals": [],
            "env_from_secret": [],
            "env_from_configmap": [],
            "memory_request": "4Gi",
            "memory_limit": "4Gi",
            "cpu_request": "250m",
            "cpu_limit": "1",
            "run_as_user": 1000,
            "run_as_group": 1000,
            "fs_group": 1000,
            "filestore_pvc": "odoo-data",
            "kopia_cache_size": "25Gi",
            "postgres_dump_size": "100Gi",
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    return _make_args
