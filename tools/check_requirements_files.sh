#!/usr/bin/bash
requirements_installed=$(mktemp /tmp/requirements.XXXXXX)
pip freeze  | LC_COLLATE=C sort > $requirements_installed
requirements_files=$(mktemp /tmp/requirements.XXXXXX)
cat requirements/requirements.*.txt | LC_COLLATE=C sort | uniq > $requirements_files
diff $requirements_installed $requirements_files
