"""Tests for odoo_kopia_snapshot.kube helpers."""

from odoo_kopia_snapshot.kube import (
    build_env_from,
    build_env_vars,
    build_pod_spec,
    build_resources,
    build_security_context,
    build_volume_mounts,
    build_volumes,
)


# -- build_env_from ----------------------------------------------------------

def test_build_env_from_empty():
    assert build_env_from([], []) == []


def test_build_env_from_secrets_only():
    result = build_env_from(["my-secret"], [])
    assert result == [{"secretRef": {"name": "my-secret"}}]


def test_build_env_from_mixed():
    result = build_env_from(["s1"], ["cm1", "cm2"])
    assert len(result) == 3
    assert result[0] == {"secretRef": {"name": "s1"}}
    assert result[1] == {"configMapRef": {"name": "cm1"}}
    assert result[2] == {"configMapRef": {"name": "cm2"}}


# -- build_env_vars -----------------------------------------------------------

def test_build_env_vars_empty():
    assert build_env_vars([], [], []) == []


def test_build_env_vars_literals():
    result = build_env_vars(["FOO=bar", "BAZ=qux"], [], [])
    assert result == [
        {"name": "FOO", "value": "bar"},
        {"name": "BAZ", "value": "qux"},
    ]


def test_build_env_vars_from_secret():
    result = build_env_vars([], ["DB_PASS=pg-secret:password"], [])
    assert result == [
        {
            "name": "DB_PASS",
            "valueFrom": {
                "secretKeyRef": {"name": "pg-secret", "key": "password"},
            },
        },
    ]


def test_build_env_vars_from_configmap():
    result = build_env_vars([], [], ["LOG_LEVEL=app-config:log-level"])
    assert result == [
        {
            "name": "LOG_LEVEL",
            "valueFrom": {
                "configMapKeyRef": {"name": "app-config", "key": "log-level"},
            },
        },
    ]


# -- build_volume_mounts ------------------------------------------------------

def test_build_volume_mounts_returns_three():
    mounts = build_volume_mounts()
    assert len(mounts) == 3
    names = {m["name"] for m in mounts}
    assert names == {"odoo-data", "kopia-cache", "postgres-dump"}


# -- build_volumes -------------------------------------------------------------

def test_build_volumes_pvc_claim():
    vols = build_volumes("my-pvc", "10Gi", "50Gi")
    pvc_vol = vols[0]
    assert pvc_vol["persistentVolumeClaim"]["claimName"] == "my-pvc"


def test_build_volumes_ephemeral_sizes():
    vols = build_volumes("pvc", "10Gi", "50Gi")
    kopia = vols[1]["ephemeral"]["volumeClaimTemplate"]["spec"]
    pg = vols[2]["ephemeral"]["volumeClaimTemplate"]["spec"]
    assert kopia["resources"]["requests"]["storage"] == "10Gi"
    assert pg["resources"]["requests"]["storage"] == "50Gi"


# -- build_resources -----------------------------------------------------------

def test_build_resources():
    res = build_resources("2Gi", "4Gi", "100m", "500m")
    assert res == {
        "requests": {"memory": "2Gi", "cpu": "100m"},
        "limits": {"memory": "4Gi", "cpu": "500m"},
    }


# -- build_security_context ----------------------------------------------------

def test_build_security_context():
    ctx = build_security_context(1000, 1000, 1000)
    assert ctx == {"runAsUser": 1000, "runAsGroup": 1000, "fsGroup": 1000}


# -- build_pod_spec ------------------------------------------------------------

def test_build_pod_spec_basic(make_args):
    args = make_args()
    spec = build_pod_spec(args, "backup", [])
    assert spec["restartPolicy"] == "Never"
    assert len(spec["containers"]) == 1
    container = spec["containers"][0]
    assert container["name"] == "backup"
    assert container["image"] == args.image
    assert container["args"] == ["backup"]


def test_build_pod_spec_extra_args(make_args):
    args = make_args()
    spec = build_pod_spec(args, "restore", ["snap123", "--verbose"])
    container = spec["containers"][0]
    assert container["args"] == ["restore", "snap123", "--verbose"]


def test_build_pod_spec_with_env(make_args):
    args = make_args(
        secret_ref=["s1"],
        env_literals=["FOO=bar"],
    )
    spec = build_pod_spec(args, "backup", [])
    container = spec["containers"][0]
    assert "envFrom" in container
    assert "env" in container


def test_build_pod_spec_no_env_when_empty(make_args):
    args = make_args()
    spec = build_pod_spec(args, "backup", [])
    container = spec["containers"][0]
    assert "envFrom" not in container
    assert "env" not in container
