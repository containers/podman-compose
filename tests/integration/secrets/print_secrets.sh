#!/bin/sh

grep . /run/secrets/*
grep . /etc/custom_location
echo "$ENV_SECRET"
