#!/usr/bin/env bash
./scripts/uninstall.sh
./scripts/clean_up.sh
python3 setup.py register
python3 setup.py sdist bdist_wheel
twine upload dist/*
