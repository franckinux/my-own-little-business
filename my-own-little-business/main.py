#!/usr/bin/env python3

import asyncio
import base64
import os

from aiohttp import web
from aiohttp_jinja2 import setup as setup_jinja
from aiohttp_session import setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aiohttp_session_flash
from aiopg.sa import create_engine
from cryptography import fernet
from jinja2 import FileSystemLoader
from sqlalchemy.engine.url import URL

from routes import setup_routes
from utils import read_configuration_file


def setup_session(app):
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    session_setup(app, EncryptedCookieStorage(secret_key))


async def attach_db(app, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

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

    app["db-engine"] = await create_engine(dsn, loop=loop)


async def detach_db(app):
    app["db-engine"].close()
    await app["db-engine"].wait_closed()


def create_app():
    config = read_configuration_file()

    app = web.Application()
    app["config"] = config

    # beware of order !
    setup_session(app)
    app.middlewares.append(aiohttp_session_flash.middleware)
    setup_jinja(
        app,
        loader=FileSystemLoader("templates"),
        context_processors=(
            aiohttp_session_flash.context_processor,
        )
    )

    setup_routes(app)

    app.on_startup.append(attach_db)
    app.on_cleanup.append(detach_db)

    return app


if __name__ == "__main__":
    app = create_app()

    web.run_app(
        app,
        host=app["config"]["http_server"]["host"],
        port=int(app["config"]["http_server"]["port"])
    )
