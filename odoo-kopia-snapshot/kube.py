"""Shared helpers for generating Kubernetes YAML manifests."""

import argparse
import shlex

import yaml


def build_env_from(secret_refs, configmap_refs):
    """Build the envFrom list for bulk Secret/ConfigMap injection."""
    items = []
    for ref in secret_refs:
        items.append({"secretRef": {"name": ref}})
    for ref in configmap_refs:
        items.append({"configMapRef": {"name": ref}})
    return items


def build_env_vars(env_literals, env_from_secret, env_from_configmap):
    """Build the env list for selective env var injection.

    env_literals: list of "NAME=VALUE" strings
    env_from_secret: list of "NAME=SECRET:KEY" strings
    env_from_configmap: list of "NAME=CONFIGMAP:KEY" strings
    """
    items = []
    for entry in env_literals:
        name, _, value = entry.partition("=")
        items.append({"name": name, "value": value})
    for entry in env_from_secret:
        name, _, ref = entry.partition("=")
        secret_name, _, key = ref.partition(":")
        items.append({
            "name": name,
            "valueFrom": {"secretKeyRef": {"name": secret_name, "key": key}},
        })
    for entry in env_from_configmap:
        name, _, ref = entry.partition("=")
        cm_name, _, key = ref.partition(":")
        items.append({
            "name": name,
            "valueFrom": {"configMapKeyRef": {"name": cm_name, "key": key}},
        })
    return items


def build_volume_mounts():
    """Build the volumeMounts list."""
    return [
        {"name": "odoo-data", "mountPath": "/var/lib/odoo"},
        {"name": "kopia-cache", "mountPath": "/tmp/kopia"},
        {"name": "postgres-dump", "mountPath": "/var/lib/odoo/database-backup"},
    ]


def build_volumes(filestore_pvc, kopia_cache_size, postgres_dump_size):
    """Build the volumes list."""
    return [
        {
            "name": "odoo-data",
            "persistentVolumeClaim": {"claimName": filestore_pvc},
        },
        {
            "name": "kopia-cache",
            "ephemeral": {
                "volumeClaimTemplate": {
                    "spec": {
                        "accessModes": ["ReadWriteOnce"],
                        "resources": {"requests": {"storage": kopia_cache_size}},
                    }
                }
            },
        },
        {
            "name": "postgres-dump",
            "ephemeral": {
                "volumeClaimTemplate": {
                    "spec": {
                        "accessModes": ["ReadWriteOnce"],
                        "resources": {"requests": {"storage": postgres_dump_size}},
                    }
                }
            },
        },
    ]


def build_resources(memory_request, memory_limit, cpu_request, cpu_limit):
    """Build the resources dict."""
    return {
        "requests": {"memory": memory_request, "cpu": cpu_request},
        "limits": {"memory": memory_limit, "cpu": cpu_limit},
    }


def build_security_context(run_as_user, run_as_group, fs_group):
    """Build the pod-level securityContext dict."""
    return {
        "runAsUser": run_as_user,
        "runAsGroup": run_as_group,
        "fsGroup": fs_group,
    }


def add_common_args(parser):
    """Add common Kubernetes manifest arguments to an argparse parser."""
    k8s_group = parser.add_argument_group("Kubernetes options")
    k8s_group.add_argument(
        "--namespace",
        required=True,
        help="Kubernetes namespace",
    )
    k8s_group.add_argument(
        "--image",
        required=True,
        help="Container image (e.g. ghcr.io/.../odoo-kopia-snapshot:2.0.1)",
    )

    env_group = parser.add_argument_group("Environment injection")
    env_group.add_argument(
        "--secret-ref",
        action="append",
        default=[],
        help="Inject all keys from a Secret via envFrom (repeatable)",
    )
    env_group.add_argument(
        "--configmap-ref",
        action="append",
        default=[],
        help="Inject all keys from a ConfigMap via envFrom (repeatable)",
    )
    env_group.add_argument(
        "--env",
        action="append",
        default=[],
        dest="env_literals",
        help="Literal env var, NAME=VALUE (repeatable)",
    )
    env_group.add_argument(
        "--env-from-secret",
        action="append",
        default=[],
        help="Single env from Secret, NAME=SECRET:KEY (repeatable)",
    )
    env_group.add_argument(
        "--env-from-configmap",
        action="append",
        default=[],
        help="Single env from ConfigMap, NAME=CONFIGMAP:KEY (repeatable)",
    )

    res_group = parser.add_argument_group("Resource limits")
    res_group.add_argument("--memory-request", default="4Gi", help="Memory request")
    res_group.add_argument("--memory-limit", default="4Gi", help="Memory limit")
    res_group.add_argument("--cpu-request", default="250m", help="CPU request")
    res_group.add_argument("--cpu-limit", default="1", help="CPU limit")

    sec_group = parser.add_argument_group("Security context")
    sec_group.add_argument(
        "--run-as-user", type=int, default=1000, help="runAsUser"
    )
    sec_group.add_argument(
        "--run-as-group", type=int, default=1000, help="runAsGroup"
    )
    sec_group.add_argument(
        "--fs-group", type=int, default=1000, help="fsGroup"
    )

    vol_group = parser.add_argument_group("Volumes")
    vol_group.add_argument(
        "--filestore-pvc",
        required=True,
        help="PVC name for the Odoo data volume",
    )
    vol_group.add_argument(
        "--kopia-cache-size",
        default="25Gi",
        help="Ephemeral volume size for Kopia cache",
    )
    vol_group.add_argument(
        "--postgres-dump-size",
        default="100Gi",
        help="Ephemeral volume size for PostgreSQL dumps",
    )

    return parser


def build_pod_spec(args, command, extra_args):
    """Build the pod spec dict (shared between CronJob and Job).

    Returns the dict for the pod template's spec field.
    """
    container = {"name": command, "image": args.image}

    env_from = build_env_from(args.secret_ref, args.configmap_ref)
    if env_from:
        container["envFrom"] = env_from

    env_vars = build_env_vars(
        args.env_literals, args.env_from_secret, args.env_from_configmap,
    )
    if env_vars:
        container["env"] = env_vars

    container["args"] = [command] + extra_args
    container["volumeMounts"] = build_volume_mounts()
    container["resources"] = build_resources(
        args.memory_request, args.memory_limit,
        args.cpu_request, args.cpu_limit,
    )

    return {
        "restartPolicy": "Never",
        "securityContext": build_security_context(
            args.run_as_user, args.run_as_group, args.fs_group,
        ),
        "containers": [container],
        "volumes": build_volumes(
            args.filestore_pvc, args.kopia_cache_size, args.postgres_dump_size,
        ),
    }


def dump_manifest(manifest):
    """Serialize a manifest dict to YAML and print to stdout."""
    print(yaml.dump(manifest, default_flow_style=False, sort_keys=False), end="")
