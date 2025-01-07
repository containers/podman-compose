#!/bin/bash

set -e

if [ $# -ne 1 ]; then
    echo "Usage: make_release.sh VERSION"
    exit 1
fi

VERSION=$1

sed "s/__version__ = .*/__version__ = \"$VERSION\"/g" -i podman_compose.py
git add podman_compose.py
git commit -m "Release $VERSION"

git tag "v$VERSION" -m "v$VERSION" -s

git push ssh://github.com/containers/podman-compose main "v$VERSION"
