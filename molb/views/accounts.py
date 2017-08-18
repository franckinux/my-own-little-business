from auth import require
from aiohttp.web import HTTPFound
import aiohttp_jinja2


@require("admin")
@aiohttp_jinja2.template("list-accounts.html")
async def list_account(request):
    async with request.app["db-pool"].acquire() as conn:
        # select unconfirmed clients
        q = (
            "SELECT id, first_name, last_name, email_address, phone_number, created_at "
            "FROM client  "
            "WHERE NOT confirmed "
            "ORDER BY created_at, last_name, first_name"
        )
        clients = await conn.fetch(q)

    return {"clients": clients}


@require("admin")
async def delete_account(request):
    client_id = int(request.match_info["id"])

    async with request.app["db-pool"].acquire() as conn:
        q = "DELETE FROM client WHERE id = $1"
        await conn.execute(q, client_id)

    return HTTPFound(request.app.router["list_account"].url_for())
