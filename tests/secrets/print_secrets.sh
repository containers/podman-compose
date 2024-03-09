#!/bin/sh

ls -la /run/secrets/*
ls -la /etc/custom_location
cat /run/secrets/*
cat /etc/custom_location
env | grep SECRET
