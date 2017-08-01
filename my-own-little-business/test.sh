#!/bin/bash
dropdb molb
createdb molb
psql molb < sql/schema.sql
python3 model-validation.py
