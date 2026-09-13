#!/bin/sh

# Updates both halves of QUI to the same release: the @qtoggle/qui npm package used by the frontend
# and the qui-server PyPI package used by the backend. The two are versioned together.
#
# Pass the version as npm spells it, e.g. 1.19.11 or 1.20.0-alpha.2. PyPI normalizes the prerelease
# spelling itself (1.20.0-alpha.2 becomes 1.20.0a2), so one argument covers both.

set -e

if [ -z "$1" ]; then
    echo "missing argument version"
    exit 1
fi

version="$1"
root="$(cd "$(dirname "$0")" && pwd)"

# Frontend: pin in package-lock.json only, leaving the "*" in package.json alone
cd "$root/qtoggleserver/frontend"
npm cache clean --force
npm install @qtoggle/qui@"$version"
git checkout package.json
sed -i 's/"jquery": "\*"/"jquery": "^3"/' package-lock.json

# Backend: pin in uv.lock only, leaving the floor in pyproject.toml alone
cd "$root"
uv lock --upgrade-package "qui-server==$version"

# Named explicitly rather than committing with -a, so that unrelated work in progress is left alone
git commit -m "Update qui to $version" qtoggleserver/frontend/package-lock.json uv.lock

