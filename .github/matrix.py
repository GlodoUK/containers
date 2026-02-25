# Generate a GitHub actions compatible output for matrix from a valid versions.yaml
# A versions.yaml is expected in the format:
# ```yaml
# thing:
# - 1.0.0
# - 2.0.0
# thing2:
# - 1.2
# ```
# The corresponding output is a matrix of thing and thing2, comprising of build_args,
# tag and versions dict
#
# In the convention of only 1 key, then a the
#
# This is intended for use with .github/workflows/build-image.yaml

import sys
import json
import itertools


MAGIC_KEYS = ("version", "release")


data = json.load(sys.stdin)

# Look for a magic __suffix key, which is assumed to be a simple string
# This is an alternative to the 'release' magic key, intended to mimic a debian-style
# patch suffix
suffix = data.pop("__suffix", False)
if not isinstance(suffix, str):
    suffix = False

keys = list(data.keys())
versions = [data[key] for key in keys]
output = []
omit_keys = len(keys) == 1

matrix_items = []
for combo in itertools.product(*versions):
    build_args = []
    tag_parts = []
    version_dict = {}

    for i, key in enumerate(keys):
        version = combo[i]
        arg_name = f"{key.upper().replace('-', '_')}_VERSION"
        build_args.append(f"{arg_name}={version}")
        # XXX: Omit key prefix when there's only one key, or it's a magic "version" key, by convention
        if omit_keys or key in MAGIC_KEYS:
            tag_parts.append(version)
        else:
            tag_parts.append(f"{key}-{version}")
        version_dict[key] = version

    tag = "-".join(tag_parts)
    if suffix:
        tag = f"{tag}+{suffix}"
    matrix_items.append(
        {
            "build_args": "\n".join(build_args),
            "tag": tag,
            "versions": version_dict,
        }
    )

result = {"include": matrix_items}
print(json.dumps(result))
