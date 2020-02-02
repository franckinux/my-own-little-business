import sys

import aiohttp_jinja2
from aiohttp_security import authorized_userid

from molb import __version__ as molb_version
from molb.auth import require


@require("client")
@aiohttp_jinja2.template("home.html")
async def home(request):
    login = await authorized_userid(request)
    async with request.app["db-pool"].acquire() as conn:
        q = "SELECT * FROM client WHERE login = $1"
        client = dict(await conn.fetchrow(q, login))
    python_version = sys.version
    return {"client": client, "version": molb_version, "version_python": python_version}
