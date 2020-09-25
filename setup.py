#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
	name='molb',
	version='0.8.3',
	description='"My Own Little Business" is a story of clients, orders, delivery places and production batches... :)',
	author='Franck Barbenoire',
	author_email='contact@franck-barbenoire.fr',
	url='https://github.com/franckinux/my-own-little-business',
	packages=find_packages(),
	include_package_data=True,
	zip_safe=False,
	license='AGPL'
)

# http://python-packaging.readthedocs.io/en/latest/command-line-scripts.html
