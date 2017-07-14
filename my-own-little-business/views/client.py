import aiohttp_jinja2
from aiohttp_security import authorized_userid
from auth import require
from sqlalchemy import select

from model import Client


@require("client")
@aiohttp_jinja2.template("client.html")
async def client_menu(request):
    login = await authorized_userid(request)
    async with request.app["db-pool"].acquire() as conn:
        q = select([Client], Client.__table__.c.login == login)
        client = dict(await conn.fetchrow(q))
    return {"client": client}
