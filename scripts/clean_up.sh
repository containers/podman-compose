#!/usr/bin/env bash

find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
find . -name "*.orig" -delete
rm -rf .cache/
rm -rf build/
rm -rf builddocs/
rm -rf dist/
rm -rf deb_dist/
rm src/podman_compose.egg-info -rf
rm builddocs.zip
