from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_babel.middlewares import _
import aiohttp_jinja2

from molb.views.auth.email_form import EmailForm
from molb.views.send_message import send_text_message
from molb.views.utils import flash
from molb.views.utils import generate_csrf_meta


@aiohttp_jinja2.template("auth/email-id.html")
async def handler(request):
    if request.method == "POST":
        form = EmailForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            data = dict(form.data.items())
            email_address = data["email_address"]
            async with request.app["db-pool"].acquire() as conn:
                q = "SELECT id, email_address, login FROM client WHERE email_address = $1"
                client = await conn.fetchrow(q, email_address)
            if client is None:
                flash(
                    request,
                    (
                        "danger",
                        _("Il n'y a pas de profil dont l'adresse email est {}").format(
                            email_address
                        )
                    )
                )
            else:
                await send_text_message(
                    request,
                    client["email_address"],
                    _("Rappel de Votre identifiant"),
                    _("Votre identifiant est {}").format(client["login"]),
                )
                flash(
                    request,
                    (
                        "info",
                        _("Un email de confirmation a été envoyé à {}").format(
                            email_address
                        )
                    )
                )
                return HTTPFound(request.app.router["login"].url_for())
        else:
            flash(request, ("danger", _("Le formulaire contient des erreurs.")))
        return {"form": form}
    elif request.method == "GET":
        form = EmailForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()
