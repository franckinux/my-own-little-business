#!/usr/bin/env python3

import argparse
import configparser
import os
import sys

from aiohttp import web
from aiohttp_jinja2 import setup as jinja_setup
from jinja2 import FileSystemLoader

from routes import setup_routes
from view import handler

def read_configuration_file():
    directory = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="my-own-little-business configuration")
    parser.add_argument("-c", "--config",
                        default=os.path.join(directory, "config", "my-own-little-business.ini"),
                        help="configuration file")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    try:
        config.read(args.config)
    except:
        sys.stderr.write("problem encountered while processing configuration file %s\n" % args.config)
        sys.exit(1)

    return config


def start_app(app_config):
    app = web.Application()

    setup_routes(app)

    jinja_setup(app, loader=FileSystemLoader("templates"))

    web.run_app(app, host=app_config["server"]["host"],
                port=int(app_config["server"]["port"]))


if __name__ == "__main__":
    config = read_configuration_file()
    start_app(config)
