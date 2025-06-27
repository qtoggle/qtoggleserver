#!/bin/bash

set -e
set -a

DATA_DEFAULT_DIR=/data.default
DATA_DIR=/data

# Ensure we have our data dir populated properly
if ! [[ -f ${DATA_DIR}/bin/activate ]] || ! [[ -f ${DATA_DIR}/bin/python ]]; then
    if ls ${DATA_DIR}/* &>/dev/null; then
        echo "Refusing to start with a non-empty data directory that is not a Python virtualenv"
        exit 1
    fi

    echo "Setting up data directory"
    mkdir -p ${DATA_DIR} && cp -r ${DATA_DEFAULT_DIR}/* ${DATA_DIR}
else
    echo "Using existing data directory"
fi

# Ensure we run a virtualenv with our Python version
DEFAULT_PYTHON_VER=$(${DATA_DEFAULT_DIR}/bin/python -V | cut -d . -f 1,2 | cut -d ' ' -f 2)
DATA_PYTHON_VER=$(${DATA_DIR}/bin/python -V | cut -d . -f 1,2 | cut -d ' ' -f 2)
if [[ "${DEFAULT_PYTHON_VER}" != "${DATA_PYTHON_VER}" ]]; then
    echo "Migrating existing virtualenv from Python ${DATA_PYTHON_VER} to Python ${DEFAULT_PYTHON_VER}"
    source ${DATA_DIR}/bin/activate
    uv pip list -q --format=freeze | grep -v 'qtoggleserver=' | cut -d '=' -f 1 > /tmp/installed-packages.txt
    deactivate
    rm -rf ${DATA_DIR:?}.bak/*
    mkdir -p ${DATA_DIR}.bak
    mv ${DATA_DIR}/* ${DATA_DIR}.bak/
    echo "Setting up data directory"
    cp -r ${DATA_DEFAULT_DIR}/* ${DATA_DIR}
    mkdir -p ${DATA_DIR}/etc
    test -f ${DATA_DIR}.bak/etc/qtoggleserver.conf && cp ${DATA_DIR}.bak/etc/qtoggleserver.conf ${DATA_DIR}/etc/
    source ${DATA_DIR}/bin/activate
    uv pip install -q -r /tmp/installed-packages.txt
else
    source ${DATA_DIR}/bin/activate
fi

# Ensure we have a conf file; use sample file by default
mkdir -p ${DATA_DIR}/etc
if ! [[ -e ${DATA_DIR}/etc/qtoggleserver.conf ]]; then
    echo "Using default qtoggleserver.conf"
    cp /usr/share/qtoggleserver/qtoggleserver.conf.sample ${DATA_DIR}/etc/qtoggleserver.conf
fi

exec "${@}"
