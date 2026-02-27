#!/usr/bin/env python3
"""Generate a Kubernetes Job manifest for odoo-kopia-snapshot restore."""

import argparse
import shlex

from kube import add_common_args, build_pod_spec, dump_manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Kubernetes Job YAML for a one-shot restore",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--name", default="kopia-restore", help="Job resource name"
    )
    parser.add_argument(
        "--snapshot",
        required=True,
        help="Kopia snapshot ID to restore",
    )
    parser.add_argument(
        "--restore-args",
        default="",
        help="Extra arguments passed to the restore command (shell-quoted string)",
    )
    add_common_args(parser)

    args = parser.parse_args()

    extra_args = [args.snapshot]
    if args.restore_args:
        extra_args.extend(shlex.split(args.restore_args))

    manifest = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": args.name,
            "namespace": args.namespace,
        },
        "spec": {
            "backoffLimit": 0,
            "ttlSecondsAfterFinished": 600,
            "template": {
                "spec": build_pod_spec(args, "restore", extra_args),
            },
        },
    }

    dump_manifest(manifest)


if __name__ == "__main__":
    main()
