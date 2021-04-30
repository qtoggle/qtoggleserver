#!/bin/bash

DATA_DIR=/data

# Ensure we have a conf file; use sample file by default
mkdir -p ${DATA_DIR}/etc
if ! [[ -e ${DATA_DIR}/etc/qtoggleserver.conf ]]; then
    echo "Using default qtoggleserver.conf"
    cp /usr/share/qtoggleserver/qtoggleserver.conf.sample ${DATA_DIR}/etc/qtoggleserver.conf
fi

# Add pip alias so that --user is automatically passed to install command
function pip() {
    if [[ "$1" == install ]]; then
        /usr/local/bin/pip install --user "${@:2}"
    else
        /usr/local/bin/pip "$@"
    fi
}


exec "${@}"
