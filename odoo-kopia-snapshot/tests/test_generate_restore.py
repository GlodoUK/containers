"""Tests for generate_restore_job manifest structure."""

from odoo_kopia_snapshot.kube import build_pod_spec


def test_restore_job_includes_snapshot_id(make_args):
    """The snapshot ID appears as the first extra arg."""
    args = make_args()
    spec = build_pod_spec(args, "restore", ["abc123"])
    container = spec["containers"][0]
    assert container["name"] == "restore"
    assert container["args"] == ["restore", "abc123"]


def test_restore_job_extra_args(make_args):
    """Additional restore args follow the snapshot ID."""
    args = make_args()
    spec = build_pod_spec(args, "restore", ["abc123", "--verbose"])
    container = spec["containers"][0]
    assert container["args"] == ["restore", "abc123", "--verbose"]


def test_restore_job_resources(make_args):
    """Custom resource values propagate to the container."""
    args = make_args(memory_request="8Gi", memory_limit="8Gi")
    spec = build_pod_spec(args, "restore", ["snap1"])
    resources = spec["containers"][0]["resources"]
    assert resources["requests"]["memory"] == "8Gi"
    assert resources["limits"]["memory"] == "8Gi"
