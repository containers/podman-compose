#!/bin/sh

echo -n "soft process limit "
ulimit -S -u
echo -n "hard process limit "
ulimit -H -u
echo -n "soft nofile limit "
ulimit -S -n
echo -n "hard nofile limit "
ulimit -H -n
