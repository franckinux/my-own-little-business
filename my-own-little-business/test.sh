#!/bin/bash
dropdb molb
createdb molb
python3 create-schema.py
python3 model-validation.py
