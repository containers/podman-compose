#!/bin/sh

sleep 10
touch /healthy

# sleep forever
dumb-init sleep infinity
