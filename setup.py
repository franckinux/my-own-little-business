#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
        name='molb',
        version='0.0.1',
        description='"My Own Little Business" is a story of clients, orders, delivery places and production batches... :)',
        author='Franck Barbenoire',
        author_email='contact@franck-barbenoire.fr',
        url='https://github.com/franckinux/my-own-little-business',
        packages=find_packages(),
        package_data={'molb': ['README.*', 'config', 'create', 'static', 'sql', 'templates']},
        include_package_data=True,
        zip_safe=False,
        license='AGPL',
        install_requires=[
            'aiohttp',
            'aiohttp_jinja2',
            'aiohttp_security',
            'aiohttp-session',
            'aiohttp-session-flash',
            'aiosmtplib',
            'asyncpg',
            'cryptography',
            'gunicorn',
            'itsdangerous',
            'passlib',
            'WTForms',
        ]
)

# http://python-packaging.readthedocs.io/en/latest/command-line-scripts.html
