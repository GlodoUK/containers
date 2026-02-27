"""Tests for generate_backup_cronjob manifest structure."""

from odoo_kopia_snapshot.kube import build_pod_spec


def test_cronjob_structure(make_args):
    """The pod spec used in a CronJob has the right shape."""
    args = make_args()
    spec = build_pod_spec(args, "backup", [])

    # Top-level pod spec keys
    assert spec["restartPolicy"] == "Never"
    assert "securityContext" in spec
    assert "volumes" in spec

    container = spec["containers"][0]
    assert container["name"] == "backup"
    assert container["args"] == ["backup"]
    assert "volumeMounts" in container
    assert "resources" in container


def test_cronjob_extra_args(make_args):
    """Extra backup args are appended to container args."""
    args = make_args()
    spec = build_pod_spec(args, "backup", ["--no-kopia-maintenance"])
    container = spec["containers"][0]
    assert container["args"] == ["backup", "--no-kopia-maintenance"]


def test_cronjob_env_injection(make_args):
    """Secret refs and env literals appear in the container."""
    args = make_args(
        secret_ref=["kopia-secret", "pg-secret"],
        env_literals=["TZ=UTC"],
    )
    spec = build_pod_spec(args, "backup", [])
    container = spec["containers"][0]

    assert len(container["envFrom"]) == 2
    assert container["envFrom"][0]["secretRef"]["name"] == "kopia-secret"
    assert container["env"][0] == {"name": "TZ", "value": "UTC"}
