#!/usr/bin/env bash
./scripts/uninstall.sh
./scripts/clean_up.sh
pyproject-build
twine upload dist/*
