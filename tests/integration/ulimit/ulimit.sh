#!/bin/sh

echo "soft process limit"
ulimit -S -u
echo "hard process limit"
ulimit -H -u
echo "soft nofile limit"
ulimit -S -n
echo "hard nofile limit"
ulimit -H -n
