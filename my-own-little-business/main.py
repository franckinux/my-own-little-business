#!/usr/bin/env python3

import argparse
import configparser
import sys

from aiohttp import web
from aiohttp_jinja2 import setup as jinja_setup
from jinja2 import FileSystemLoader

from routes import setup_routes
from utils import read_configuration_file
from view import handler


def start_app(config):
    config = config["http_server"]

    app = web.Application()

    setup_routes(app)

    jinja_setup(app, loader=FileSystemLoader("templates"))

    web.run_app(
        app,
        host=config["host"],
        port=int(config["port"])
    )


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)
    start_app(config)
