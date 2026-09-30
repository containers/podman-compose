#!/bin/sh

grep . /run/secrets/*
echo "CUSTOM_LOCATION:"
grep . /etc/custom_location
echo "ENV_SECRET=$ENV_SECRET"
