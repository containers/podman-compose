#!/bin/sh

# Delete repository dir
rm -rf podman-compose-src

# Clone repository
git clone https://github.com/containers/podman-compose podman-compose-src

# Generate binary
sh podman-compose-src/scripts/generate_binary_using_dockerfile.sh

# Move binary outside repo's dir
mv podman-compose-src/podman-compose .

# Delete repository dir
rm -rf podman-compose-src
