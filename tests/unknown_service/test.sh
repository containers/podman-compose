#!/bin/sh

PODMAN_COMPOSE="${PODMAN_COMPOSE:-../../podman_compose.py}"

failed=false
commands='build up down run exec start stop restart logs'

for cmd in $commands; do
  $PODMAN_COMPOSE "$cmd" xyz 2>/dev/null
  exit_code=$?
  if [ $exit_code -ne 1 ]; then
    echo "Expected command $cmd to exit with code 1 for unknown service, got exit code $exit_code"
    failed=true
  fi
done

if $failed; then
  exit 1
fi
