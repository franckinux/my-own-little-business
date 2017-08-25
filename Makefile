.PHONY: pep8 print_sources

print_sources:
	tools/print.sh

pep8:
	pyflakes3 create molb/auth molb/error.py molb/main.py molb/views molb/routes.py molb/utils.py tools
