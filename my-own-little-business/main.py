#!/usr/bin/env python3

import asyncio
import base64
import os

from aiohttp import web
from aiohttp_jinja2 import setup as setup_jinja
from aiohttp_session import setup as session_setup
from aiohttp_security import authorized_userid
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_security import SessionIdentityPolicy
from aiohttp_security import setup as setup_security
import aiohttp_session_flash
from asyncpg import create_pool
from cryptography import fernet
from jinja2 import FileSystemLoader

from auth.db_auth import DBAuthorizationPolicy
from error import error_middleware
from routes import setup_routes
from views.order import translate_mode
from utils import read_configuration_file


def setup_session(app):
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    session_setup(app, EncryptedCookieStorage(secret_key))


async def attach_db(config, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    config["database"]["password"] = os.getenv("PG_PASS", "") or config["database"]["password"]

    dsn = "postgres://{}:{}@{}:{}/{}".format(
        config["database"]["username"], config["database"]["password"],
        config["database"]["host"], config["database"]["port"],
        config["database"]["database"]
    )
    return await create_pool(dsn=dsn, loop=loop)


async def detach_db(app):
    await app["db-pool"].close()


async def authorized_userid_context_processor(request):
    return {
        "authorized_userid": await authorized_userid(request)
    }


async def create_app(loop):
    config = read_configuration_file()
    db_pool = await attach_db(config)

    app = web.Application(middlewares=[error_middleware])
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
        filters={"translate_mode": translate_mode},
        context_processors=(
            aiohttp_session_flash.context_processor,
            authorized_userid_context_processor
        )
    )

    setup_routes(app)

    app.on_cleanup.append(detach_db)

    return app


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(create_app(loop))

    web.run_app(
        app,
        host=app["config"]["http_server"]["host"],
        port=int(app["config"]["http_server"]["port"])
    )
