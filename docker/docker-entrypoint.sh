#!/bin/bash

set -e
set -a

DATA_DIR=/data

# Ensure we have our data dir populated properly
if ! [[ -f ${DATA_DIR}/bin/activate ]] || ! [[ -f ${DATA_DIR}/bin/python ]]; then
    echo "Setting up virtualenv in data directory"
    uv venv -q --allow-existing --system-site-packages ${DATA_DIR}
else
    echo "Using existing virtualenv in data directory"
fi

# Ensure we run a virtualenv with our Python version
WANTED_PYTHON_VER=$(/usr/local/bin/python -V | cut -d . -f 1,2 | cut -d ' ' -f 2)
DATA_PYTHON_VER=$(${DATA_DIR}/bin/python -V | cut -d . -f 1,2 | cut -d ' ' -f 2)
#if [[ "${WANTED_PYTHON_VER}" != "${DATA_PYTHON_VER}" ]]; then
if true; then
    echo "Migrating existing virtualenv from Python ${DATA_PYTHON_VER} to Python ${WANTED_PYTHON_VER}"
    echo "Backing up list of installed packages"
    source ${DATA_DIR}/bin/activate
    uv pip list -q --format=freeze | grep -v 'qtoggleserver=' | cut -d '=' -f 1 > /tmp/installed-packages.txt
    deactivate
    echo "Backing up data directory"
    rm -rf ${DATA_DIR:?}.bak/*
    mkdir -p ${DATA_DIR}.bak
    mv ${DATA_DIR}/* ${DATA_DIR}.bak/
    echo "Setting up virtualenv in data directory"
    uv venv -q --allow-existing --system-site-packages ${DATA_DIR}
    mkdir -p ${DATA_DIR}/etc
    test -f ${DATA_DIR}.bak/etc/qtoggleserver.conf && cp ${DATA_DIR}.bak/etc/qtoggleserver.conf ${DATA_DIR}/etc/
    echo "Activating virtualenv in data directory"
    source ${DATA_DIR}/bin/activate
    echo "Installing previously installed packages"
    uv pip install -q -r /tmp/installed-packages.txt
else
    echo "Activating virtualenv in data directory"
    source ${DATA_DIR}/bin/activate
fi

# Ensure we have a conf file; use sample file by default
mkdir -p ${DATA_DIR}/etc
if ! [[ -e ${DATA_DIR}/etc/qtoggleserver.conf ]]; then
    echo "Using default qtoggleserver.conf"
    cp /usr/share/qtoggleserver/qtoggleserver.conf.sample ${DATA_DIR}/etc/qtoggleserver.conf
fi

# Ensure extra required packages are installed
if [[ -f ${DATA_DIR}/requirements.txt ]]; then
    echo "Installing packages from requirements.txt"
    uv pip install -q -r ${DATA_DIR}/requirements.txt
    rm -f ${DATA_DIR}/requirements.txt
fi

exec "${@}"
