if [[ -n "$VIRTUAL_ENV" ]]; then
   export PIP_REQUIRE_VIRTUALENV=false
   export PIP_USER=true
   export PYTHONPATH=''

   deactivate
fi
