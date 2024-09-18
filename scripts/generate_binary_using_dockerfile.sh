#!/bin/sh

# Find an available container tool (docker or podman)
find_container_tool() {
    if command -v docker > /dev/null 2>&1; then
        echo "sudo docker"
    elif command -v podman > /dev/null 2>&1; then
        echo "podman"
    else
        echo "Error: Neither docker nor podman is available." >&2
        exit 1
    fi
}

# Determine which container tool to use
CONTAINER_TOOL=$(find_container_tool)

# Locate the directory containing dockerfile (root)
PROJECT_ROOT_DIR="$(cd "$(dirname "$0")" && pwd)/.."

# Check SELinux status and set appropriate mount option
check_selinux() {
    if command -v getenforce > /dev/null 2>&1; then
        SELINUX_STATUS=$(getenforce)
        if [ "$SELINUX_STATUS" = "Enforcing" ] || [ "$SELINUX_STATUS" = "Permissive" ]; then
            echo ":z"
        else
            echo ""
        fi
    elif [ -f /sys/fs/selinux/enforce ]; then
        if [ "$(cat /sys/fs/selinux/enforce)" = "1" ]; then
            echo ":z"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Get the SELinux option for volume mounts if SELinux is enforcing or permissive
SELINUX=$(check_selinux)

# Build binary
$CONTAINER_TOOL image rm build-podman-compose

if expr "$CONTAINER_TOOL" : '.*docker.*' >/dev/null; then
    $CONTAINER_TOOL build -t build-podman-compose "$PROJECT_ROOT_DIR"
    $CONTAINER_TOOL run --name build-podman-compose build-podman-compose
    $CONTAINER_TOOL cp build-podman-compose:/result/podman-compose "$PROJECT_ROOT_DIR/podman-compose"
    $CONTAINER_TOOL container stop build-podman-compose
    $CONTAINER_TOOL container rm -f build-podman-compose
else
    $CONTAINER_TOOL build -v "$PROJECT_ROOT_DIR:/result$SELINUX" -t build-podman-compose "$PROJECT_ROOT_DIR"
fi
$CONTAINER_TOOL image rm python:3.11-slim
$CONTAINER_TOOL image rm build-podman-compose
