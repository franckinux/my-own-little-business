.PHONY: clear create requirements print_sources serve venv

clean:
	rm -rf venv

venv:
	python3 -m venv venv

requirements:
	pip3 install -r requirements.txt

create:
	dropdb molb
	createdb molb
	psql molb < create/schema.sql
	PYTHONPATH=. python3 create/create.py
	PYTHONPATH=. python3 create/secret_keys.py

serve:
	venv/bin/gunicorn main:app --bind 127.0.0.1:8080 --reload --worker-class aiohttp.GunicornWebWorker

print_sources:
	tools/print.sh

pep8:
	pyflakes3 auth create tools views main.py error.py routes.py utils.py
