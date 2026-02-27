#!/usr/bin/env python3
"""Generate a Kubernetes CronJob manifest for odoo-kopia-snapshot backup."""

import argparse
import shlex

from kube import add_common_args, build_pod_spec, dump_manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Kubernetes CronJob YAML for scheduled backups",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--name", default="kopia-backup", help="CronJob resource name"
    )
    parser.add_argument(
        "--schedule", default="0 0 * * *", help="Cron schedule expression"
    )
    parser.add_argument(
        "--backup-args",
        default="",
        help="Extra arguments passed to the backup command (shell-quoted string)",
    )
    add_common_args(parser)

    args = parser.parse_args()

    extra_args = shlex.split(args.backup_args) if args.backup_args else []

    manifest = {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {
            "name": args.name,
            "namespace": args.namespace,
        },
        "spec": {
            "schedule": args.schedule,
            "concurrencyPolicy": "Forbid",
            "jobTemplate": {
                "spec": {
                    "backoffLimit": 0,
                    "template": {
                        "spec": build_pod_spec(args, "backup", extra_args),
                    },
                },
            },
        },
    }

    dump_manifest(manifest)


if __name__ == "__main__":
    main()
