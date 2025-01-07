#!/bin/bash

set -e

if [ $# -ne 1 ]; then
    echo "Usage: make_release_notes.sh VERSION"
    exit 1
fi

VERSION=$1
towncrier build --version "$VERSION" --yes
git mv "docs/Changelog-new.md" "docs/Changelog-$VERSION.md"
git add "newsfragments/"
git commit -m "Release notes for $VERSION"
