from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from wtforms import IntegerField
from wtforms import StringField
from wtforms import SubmitField

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data


class ClientIdForm(CsrfForm):
    client_id = IntegerField("Id du client")
    client_last_name = StringField("Nom du client")
    submit = SubmitField("Valider")


@require("admin")
@aiohttp_jinja2.template("list-client.html")
async def list_client(request):
    if request.method == "POST":
        form = ClientIdForm(await request.post(), meta=await generate_csrf_meta(request))

        async with request.app["db-pool"].acquire() as conn:
            data = remove_special_data(await request.post())
            if form.validate():
                client_id = int(data["client_id"])
                q = (
                    "SELECT c.id, c.first_name, c.last_name, c.wallet, "
                    "       c.disabled, SUM(o.total) AS total "
                    "FROM order_ AS o "
                    "INNER JOIN client AS c ON o.client_id = c.id "
                    "WHERE c.id = $1 AND o.payment_id IS NULL AND NOT c.super_user "
                    "GROUP BY c.id, c.first_name, c.last_name, c.wallet, "
                    "         c.disabled"
                )
                clients = await conn.fetch(q, client_id)
            else:
                client_last_name = data["client_last_name"]
                if client_last_name.strip() == "":
                    q = (
                        "SELECT c.id, c.first_name, c.last_name, c.wallet, "
                        "       c.disabled, SUM(o.total) AS total "
                        "FROM order_ AS o "
                        "INNER JOIN client AS c ON o.client_id = c.id "
                        "WHERE o.payment_id IS NULL AND NOT c.super_user "
                        "GROUP BY c.id, c.first_name, c.last_name, c.wallet, "
                        "         c.disabled "
                        "ORDER BY c.id"
                    )
                    clients = await conn.fetch(q)
                else:
                    q = (
                        "SELECT c.id, c.first_name, c.last_name, c.wallet, "
                        "       c.disabled, SUM(o.total) AS total "
                        "FROM order_ AS o "
                        "INNER JOIN client AS c ON o.client_id = c.id "
                        "WHERE c.last_name = $1 AND o.payment_id IS NULL AND "
                        "      NOT c.super_user "
                        "GROUP BY c.id, c.first_name, c.last_name, c.wallet, "
                        "         c.disabled "
                        "ORDER BY c.id"
                    )
                    clients = await conn.fetch(q, client_last_name)

            return {"form": form, "clients": clients}
    elif request.method == "GET":
        form = ClientIdForm(meta=await generate_csrf_meta(request))
        async with request.app["db-pool"].acquire() as conn:
            q = (
                "SELECT c.id, c.first_name, c.last_name, c.wallet, "
                "       c.disabled, SUM(o.total) AS total "
                "FROM order_ AS o "
                "INNER JOIN client AS c ON o.client_id = c.id "
                "WHERE o.payment_id IS NULL AND NOT c.super_user "
                "GROUP BY c.id, c.first_name, c.last_name, c.wallet, "
                "         c.disabled "
                "ORDER BY c.id"
            )
            clients = await conn.fetch(q)
        return {"form": form, "clients": clients}
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
