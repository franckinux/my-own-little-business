if [[ -f .venv/bin/activate ]]; then
   export PIP_REQUIRE_VIRTUALENV=true
   export PIP_USER=false
   export PYTHONPATH=$(readlink -f .)

   source .venv/bin/activate
fi
