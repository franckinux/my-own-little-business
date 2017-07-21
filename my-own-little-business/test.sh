#!/bin/bash
dropdb molb
createdb molb
psql molb < sql/create-db.sql
python3 model-validation.py
