from aiohttp.web import HTTPFound
from aiohttp_babel.middlewares import _
import aiohttp_jinja2
from aiohttp_session_flash import flash

from molb.auth import require
from molb.views.send_message import send_confirmation


@require("admin")
@aiohttp_jinja2.template("list-unconfirmed.html")
async def list_unconfirmed(request):
    async with request.app["db-pool"].acquire() as conn:
        # select unconfirmed clients
        q = (
            "SELECT CAST(id AS TEXT), first_name, last_name, email_address, phone_number, created_at "
            "FROM client "
            "WHERE NOT confirmed "
            "ORDER BY created_at, last_name, first_name"
        )
        clients = await conn.fetch(q)

    return {"clients": clients}


@require("admin")
async def delete_unconfirmed(request):
    client_id = int(request.match_info["id"])

    async with request.app["db-pool"].acquire() as conn:
        q = "DELETE FROM client WHERE id = $1 AND NOT confirmed"
        await conn.execute(q, client_id)

    return HTTPFound(request.app.router["list_unconfirmed"].url_for())


@require("admin")
async def send_unconfirmed(request):
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
        _("Confirmation de votre enregistrement"),
        "register-confirmation"
    )
    flash(
        request,
        (
            "info",
            _("Un message de confirmation a été envoyé à {}").format(email_address)
        )
    )
    return HTTPFound(request.app.router["list_unconfirmed"].url_for())
