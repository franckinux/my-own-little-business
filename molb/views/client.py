from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash

from molb.auth import require
from molb.views.send_message import send_confirmation


@require("admin")
@aiohttp_jinja2.template("list-client.html")
async def list_client(request):
    if request.method == "GET":
        async with request.app["db-pool"].acquire() as conn:
            q = (
                "SELECT id, first_name, last_name, confirmed, disabled "
                "FROM client "
                "WHERE NOT super_user "
                "ORDER BY last_name, first_name"
            )
            clients = await conn.fetch(q)
        return {"clients": clients}
    else:
        raise HTTPMethodNotAllowed()


@require("admin")
async def confirm_client(request):
    client_id = int(request.match_info["id"])
    async with request.app["db-pool"].acquire() as conn:
        q = "SELECT email_address FROM client WHERE id = $1"
        row = await conn.fetchrow(q, client_id)
        email_address = row["email_address"]
    await send_confirmation(
        request,
        email_address,
        {"id": client_id},
        "confirm_register",
        "Confirmation de votre enregistrement",
        "register-confirmation"
    )
    flash(
        request,
        (
            "info",
            "Un message de confirmation a été envoyé à {}".format(email_address)
        )
    )
    return HTTPFound(request.app.router["list_client"].url_for())


@require("admin")
async def toggle_client(request):
    client_id = int(request.match_info["id"])
    async with request.app["db-pool"].acquire() as conn:
        q = "UPDATE client SET disabled = NOT disabled WHERE id = $1"
        await conn.execute(q, client_id)
    flash(request, ("success", "Le statut du client a été modifié."))
    return HTTPFound(request.app.router["list_client"].url_for())
