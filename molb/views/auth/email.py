from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_babel.middlewares import _
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
    login = await authorized_userid(request)
    async with request.app["db-pool"].acquire() as conn:
        q = "SELECT id, email_address FROM client WHERE login = $1"
        client = await conn.fetchrow(q, login)

        if request.method == "POST":
            form = EmailForm(await request.post(), meta=await generate_csrf_meta(request))

            if form.validate():
                data = dict(form.data.items())
                email_address = data["email_address"]

                q = "SELECT COUNT(*) FROM client WHERE email_address = $1"
                if await conn.fetchval(q, email_address) != 0:
                    flash(request, ("danger", _("Veuillez choisir une autre adresse email")))
                    return {"form": form, "email": client["email_address"]}

                await send_confirmation(
                    request,
                    email_address,
                    {"id": client["id"], "email_address": email_address},
                    "confirm_email",
                    _("Changement d'adresse email"),
                    "email-confirmation"
                )
                flash(
                    request,
                    (
                        "info",
                        _("Un mail de confirmation a été envoyé à {}").format(
                            email_address
                        )
                    )
                )
                return HTTPFound(request.app.router["home"].url_for())
            else:
                flash(request, ("danger", _("Le formulaire contient des erreurs")))
            return {"form": form, "email": client["email_address"]}
        elif request.method == "GET":
            form = EmailForm(meta=await generate_csrf_meta(request))
            return {"form": form, "email": client["email_address"]}
        else:
            raise HTTPMethodNotAllowed()


async def confirm(request):
    token = request.match_info["token"]
    try:
        token_data = get_token_data(token, request.app["config"]["application"]["secret_key"])
        id_ = token_data["id"]
        email_address = token_data["email_address"]
    except Exception:
        flash(request, ("danger", _("Le lien est invalide ou a expiré")))
        raise HTTPBadRequest()

    async with request.app["db-pool"].acquire() as conn:
        q = "UPDATE client SET email_address = $1 WHERE id = $2"
        try:
            await conn.execute(q, email_address, id_)
        except Exception:
            flash(request, ("danger", _("Votre adresse email ne peut pas être modifiée")))
        else:
            flash(request, ("info", _("Votre adresse email a été modifiée")))
        login = await authorized_userid(request)
        if login:
            return HTTPFound(request.app.router["home"].url_for())
        else:
            return HTTPFound(request.app.router["login"].url_for())
