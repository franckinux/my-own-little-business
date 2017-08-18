#!/bin/bash
set -e
export PYTHONPATH=..
dropdb molb
createdb molb
psql molb < schema.sql
python3 install.py
python3 secret_keys.py
if [ "$1" == "-p" ] ; then
    python3 populate.py
fi
