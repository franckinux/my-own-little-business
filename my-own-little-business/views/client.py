import aiohttp_jinja2
from aiohttp_security import authorized_userid
from auth.decorators import require
from sqlalchemy import select

from model import Batch
from model import Client


@require("client")
@aiohttp_jinja2.template("client.html")
async def client_menu(request):
    login = await authorized_userid(request)
    async with request.app["db-engine"].acquire() as conn:
        q = select([Client], Client.__table__.c.login == login)
        result = await conn.execute(q)
        client = dict(await result.fetchone())
    return {"client": client}
