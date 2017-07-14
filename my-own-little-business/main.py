#!/usr/bin/env python3

import asyncio
import base64
import os

from aiohttp import web
from aiohttp_jinja2 import setup as setup_jinja
from aiohttp_session import setup as session_setup
# TODO : use encrypted cookies in production !
from aiohttp_session import SimpleCookieStorage
# from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_security import SessionIdentityPolicy
from aiohttp_security import setup as setup_security
import aiohttp_session_flash
from asyncpgsa import create_pool
from cryptography import fernet
from jinja2 import FileSystemLoader
from sqlalchemy.engine.url import URL

from auth.db_auth import DBAuthorizationPolicy
from routes import setup_routes
from utils import read_configuration_file


def setup_session(app):
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    # TODO : use encrypted cookies in production !
    # session_setup(app, EncryptedCookieStorage(secret_key))
    session_setup(app, SimpleCookieStorage())  # /!\ Not suitable for production !!!


async def attach_db(config, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

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

    return await create_pool(dsn=dsn, loop=loop)


async def detach_db(app):
    await app["db-pool"].close()


async def create_app():
    config = read_configuration_file()
    db_pool = await attach_db(config)

    app = web.Application()
    app["config"] = config
    app["db-pool"] = db_pool

    # beware of order !
    setup_session(app)
    setup_security(
        app,
        SessionIdentityPolicy(),
        DBAuthorizationPolicy(db_pool)
    )
    app.middlewares.append(aiohttp_session_flash.middleware)
    setup_jinja(
        app,
        loader=FileSystemLoader("templates"),
        context_processors=(
            aiohttp_session_flash.context_processor,
        )
    )

    setup_routes(app)

    app.on_cleanup.append(detach_db)

    return app


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(create_app())

    web.run_app(
        app,
        host=app["config"]["http_server"]["host"],
        port=int(app["config"]["http_server"]["port"])
    )
