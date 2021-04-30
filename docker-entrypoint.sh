#!/bin/bash

DATA_DIR=/data

if ! [[ -e ${DATA_DIR} ]]; then
    echo "WARNING: your data dir will be lost when container exits!"
fi

# Ensure we have a conf file; use sample file by default
mkdir -p ${DATA_DIR}/etc
if ! [[ -e ${DATA_DIR}/etc/qtoggleserver.conf ]]; then
    echo "Using default qtoggleserver.conf"
    cp /usr/share/qtoggleserver/qtoggleserver.conf.sample ${DATA_DIR}/etc/qtoggleserver.conf
fi

exec "${@}"
