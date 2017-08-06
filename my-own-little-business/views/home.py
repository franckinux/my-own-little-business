import aiohttp_jinja2
from aiohttp_security import authorized_userid
from auth import require


@require("client")
@aiohttp_jinja2.template("home.html")
async def home(request):
    login = await authorized_userid(request)
    async with request.app["db-pool"].acquire() as conn:
        q = "SELECT * FROM client WHERE login = $1"
        client = dict(await conn.fetchrow(q, login))
    return {"client": client}
