#!/usr/bin/env python3

import asyncio
import base64
import os
import os.path as op

from aiohttp import web
from aiohttp_babel.locale import load_gettext_translations
from aiohttp_babel.locale import set_default_locale
from aiohttp_babel.middlewares import _
from aiohttp_babel.middlewares import babel_middleware
import aiohttp_jinja2
from aiohttp_session import setup as session_setup
from aiohttp_security import authorized_userid
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_security import SessionIdentityPolicy
from aiohttp_security import setup as setup_security
import aiohttp_session_flash
from asyncpg import create_pool
from jinja2 import FileSystemLoader

from molb.auth.db_auth import DBAuthorizationPolicy
from molb.error import error_middleware
from molb.routes import setup_routes
from molb.views.send_message import MassMailer
from molb.utils import read_configuration_file


def setup_i18n():
    set_default_locale("fr")
    locales_dir = op.join(op.dirname(op.abspath(__file__)), "locales", "translations")
    load_gettext_translations(locales_dir, "messages")


def setup_session(app):
    # use the same session key for all instances of the application
    # as gunicorn can create more than one
    fernet_key = app["config"]["application"]["session_secret_key"]
    secret_key = base64.urlsafe_b64decode(fernet_key)
    session_setup(app, EncryptedCookieStorage(secret_key))


async def attach_db(config):
    config["database"]["password"] = os.getenv("PG_PASS", "") or config["database"]["password"]

    dsn = "postgres://{}:{}@{}:{}/{}".format(
        config["database"]["username"], config["database"]["password"],
        config["database"]["host"], config["database"]["port"],
        config["database"]["database"]
    )
    return await create_pool(dsn=dsn)


async def startup(app):
    db_pool = await attach_db(app["config"])
    app["db-pool"] = db_pool

    setup_security(
        app,
        SessionIdentityPolicy(),
        DBAuthorizationPolicy(db_pool)
    )


async def cleanup(app):
    await app["db-pool"].close()
    app["mailer"].close()


async def authorized_userid_context_processor(request):
    return {"authorized_userid": await authorized_userid(request)}


async def create_app():
    config = read_configuration_file()

    app = web.Application(middlewares=[error_middleware, babel_middleware])
    app["config"] = config

    app["mailer"] = MassMailer()

    # beware of order !
    setup_session(app)
    app.middlewares.append(aiohttp_session_flash.middleware)

    template_dir = op.join(op.dirname(op.abspath(__file__)), "templates")
    aiohttp_jinja2.setup(
        app,
        loader=FileSystemLoader(template_dir),
        context_processors=(
            aiohttp_session_flash.context_processor,
            authorized_userid_context_processor
        )
    )
    jinja2_env = aiohttp_jinja2.get_env(app)
    jinja2_env.globals['_'] = _

    setup_routes(app)

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)

    return app


setup_i18n()
loop = asyncio.get_event_loop()
app = loop.run_until_complete(create_app())

if __name__ == "__main__":

    web.run_app(
        app,
        host=app["config"]["http_server"]["host"],
        port=int(app["config"]["http_server"]["port"])
    )
