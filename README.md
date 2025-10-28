# Containers

A collection of containers that we use day-to-day at Glo.
This repository is a mono-repo that amalgamates several other repositories to ease our
maintenance burden.

Whilst the code is open source we have typically built these modules for ourselves, or for customers. As such all support outside of our customer base is limited/at our discretion.
We are happy to accept contributions.
All modules in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, performance, or stability.
If you require support please contact us via glo.systems.

## How it works
- Each directory should refer to a specific container. The name of the directory will be
  used as the container image name.
- Within each directory there **MUST** be a versions.yaml and a Dockerfile at minimum.
- Although not required, a README.md in each directory is always nice.
- The versions.yaml describes a matrix of inputs, which will be used to build the
  Dockerfile.
- We use renovate annotations to help automatically bump versions.
  - Additional packageRules may be required.
- GitHub actions are used to detect changes at a directory level, which then delegates
  to a secondary build action
