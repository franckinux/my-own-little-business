export PYTHONPATH=$(readlink -f .)
export MOLB_CONFIG=$(readlink -f .)/config/my-own-little-business-dev.ini

if [[ -d .venv ]]; then
   source .venv/bin/activate
fi
