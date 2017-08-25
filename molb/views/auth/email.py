from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_security import authorized_userid
from aiohttp_session_flash import flash

from molb.auth import require
from molb.views.auth.email_form import EmailForm
from molb.views.auth.token import get_token_data
from molb.views.send_message import send_confirmation
from molb.views.utils import generate_csrf_meta


@require("client")
@aiohttp_jinja2.template("auth/email-email.html")
async def handler(request):
    if request.method == "POST":

        form = EmailForm(await request.post(), meta=await generate_csrf_meta(request))

        if form.validate():
            data = dict(form.data.items())
            email_address = data["email_address"]

            login = await authorized_userid(request)
            async with request.app["db-pool"].acquire() as conn:
                q = "SELECT id, email_address FROM client WHERE login = $1"
                client = await conn.fetchrow(q, login)
            await send_confirmation(
                request,
                email_address,
                {"id": client["id"], "email_address": email_address},
                "confirm_email",
                "Changement d'adresse mail",
                "email-confirmation"
            )
            flash(
                request,
                (
                    "info",
                    "Un mail de confirmation a été envoyé à {}".format(
                        email_address
                    )
                )
            )
            return HTTPFound(request.app.router["home"].url_for())
        else:
            flash(request, ("danger", "Le formulaire comporte des erreurs"))
        return {"form": form}
    elif request.method == "GET":
        form = EmailForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


async def confirm(request):
    token = request.match_info["token"]
    try:
        token_data = get_token_data(token, request.app["config"]["application"]["secret_key"])
        id_ = token_data["id"]
        email_address = token_data["email_address"]
    except:
        flash(request, ("danger", "Le lien est invalide ou a expiré"))
        raise HTTPBadRequest()

    async with request.app["db-pool"].acquire() as conn:
        q = "UPDATE client SET email_address = $1 WHERE id = $2"
        try:
            await conn.execute(q, email_address, id_)
        except:
            flash(request, ("danger", "Votre adresse mail ne peut pas être modifiée"))
        else:
            flash(request, ("info", "Votre adresse mail a bien été modifiée"))
        return HTTPFound(request.app.router["login"].url_for())
