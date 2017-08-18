.PHONY: clear venv requirements install serve

clean:
	rm -rf venv

venv:
	python3 -m venv venv

requirements:
	pip3 install -r requirements.txt

install:
	dropdb molb
	createdb molb
	psql molb < install/schema.sql
	PYTHONPATH=. python3 install/install.py
	PYTHONPATH=. python3 install/secret_keys.py

serve:
	venv/bin/gunicorn main:app --bind 127.0.0.1:8080 --reload --worker-class aiohttp.GunicornWebWorker
