#!/usr/bin/env python3

import argparse
import configparser
import os
import sys

from aiohttp import web
from aiohttp_jinja2 import setup as jinja_setup
from aiopg.sa import create_engine
from jinja2 import FileSystemLoader
import sqlalchemy as sa
from sqlalchemy.engine.url import URL

from routes import setup_routes
from utils import read_configuration_file
from view import handler


async def attach_db(app):
    config = app["config"]
    config["database"]["password"] = os.getenv("PG_PASS", "") or config["database"]["password"]

    db_connection_infos = {
        "drivername": "postgres",
        "host": config["database"]["host"],
        "port": config["database"]["port"],
        "username": config["database"]["username"],
        "password": config["database"]["password"],
        "database": config["database"]["database"]
    }
    dsn = str(URL(**db_connection_infos))

    app["db"] = await create_engine(dsn)


async def detach_db(app):
    app["db"].close()
    await app["db"].wait_closed()
    app["db"] = None


def start_app(config):
    app = web.Application()
    app["config"] = config

    setup_routes(app)

    jinja_setup(app, loader=FileSystemLoader("templates"))

    app.on_startup.append(attach_db)
    app.on_shutdown.append(detach_db)

    web.run_app(
        app,
        host=config["http_server"]["host"],
        port=int(config["http_server"]["port"])
    )


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)

    start_app(config)
