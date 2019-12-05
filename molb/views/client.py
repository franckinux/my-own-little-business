from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash

from molb.auth import require


@require("admin")
@aiohttp_jinja2.template("list-client.html")
async def list_client(request):
    if request.method == "GET":
        async with request.app["db-pool"].acquire() as conn:
            q = (
                "SELECT c.id, c.first_name, c.last_name, "
                "       c.disabled, SUM(o.total) AS total "
                "FROM order_ AS o "
                "INNER JOIN client AS c ON o.client_id = c.id "
                "WHERE NOT c.super_user "
                "GROUP BY c.id, c.first_name, c.last_name, c.disabled "
            )
            clients = await conn.fetch(q)
        return {"clients": clients}
    else:
        raise HTTPMethodNotAllowed()


@require("admin")
async def toggle_client(request):
    client_id = int(request.match_info["id"])
    async with request.app["db-pool"].acquire() as conn:
        q = "UPDATE client SET disabled = NOT disabled WHERE id = $1"
        await conn.execute(q, client_id)
    flash(request, ("success", "Le statut du client a été modifié."))
    return HTTPFound(request.app.router["list_client"].url_for())
