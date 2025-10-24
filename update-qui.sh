#!/bin/sh

if [ -z "$1" ]; then
    echo "missing argument version"
    exit 1
fi

cd $(dirname $0)/qtoggleserver/frontend
npm cache clean
npm install @qtoggle/qui@$1
git checkout package.json
git commit -am "frontend: Update qui to $1"
