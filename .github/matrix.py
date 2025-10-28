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
# This is intended for use with .github/workflows/build-image.yaml

import sys
import json
import itertools

data = json.load(sys.stdin)

keys = list(data.keys())
versions = [data[key] for key in keys]
output = []

matrix_items = []
for combo in itertools.product(*versions):
  build_args = []
  tag_parts = []
  version_dict = {}

  for i, key in enumerate(keys):
    version = combo[i]
    arg_name = f"{key.upper().replace('-', '_')}_VERSION"
    build_args.append(f"{arg_name}={version}")
    tag_parts.append(f"{key}-{version}")
    version_dict[key] = version

  matrix_items.append({
    "build_args": "\n".join(build_args),
    "tag": "-".join(tag_parts),
    "versions": version_dict
  })

result = {"include": matrix_items}
print(json.dumps(result))
