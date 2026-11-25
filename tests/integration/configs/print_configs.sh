#!/bin/sh

grep . \
    /podman_compose_test_config \
    /podman_compose_test_config_2 \
    /file_config \
    /etc/custom_location \
    /unused_params_warning \
    /content_config \
    /content_config_with_var \
    /environment_config
