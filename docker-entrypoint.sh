#!/bin/bash

DATA_DIR=/data
VENV_DIR=${DATA_DIR}

# Ensure we run from a virtual environment, but only if data volume has been mounted
if [[ -e ${DATA_DIR} ]]; then
    if ! [[ -e ${VENV_DIR}/bin/python ]]; then
        echo "Creating virtualenv"
        virtualenv --system-site-packages ${VENV_DIR}
    fi

    source ${VENV_DIR}/bin/activate
else
    echo "Running without data volume"
    mkdir ${DATA_DIR}
fi

# Ensure we have a conf file; use sample file by default
mkdir -p ${DATA_DIR}/etc
if ! [[ -e ${DATA_DIR}/etc/qtoggleserver.conf ]]; then
    echo "Using default qtoggleserver.conf"
    cp /usr/share/qtoggleserver/qtoggleserver.conf.sample ${DATA_DIR}/etc/qtoggleserver.conf
fi

exec "${@}"
