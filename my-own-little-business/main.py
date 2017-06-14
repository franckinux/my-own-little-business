#!/usr/bin/env python3

import argparse
# import asyncio
from aiohttp import web
import configparser
from importlib.machinery import SourceFileLoader
import os
import sys


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
    # app["config"] = app_config

    web.run_app(app, host=app_config["host"], port=int(app_config["port"]))


if __name__ == "__main__":
    config = read_configuration_file()
    import pdb; pdb.set_trace()
    start_app(config["server"])
