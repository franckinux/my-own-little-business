from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_babel.middlewares import _
import aiohttp_jinja2
from passlib.hash import sha256_crypt
from wtforms import PasswordField
from wtforms import SubmitField
from wtforms.validators import EqualTo
from wtforms.validators import Length
from wtforms.validators import DataRequired

from molb.views.auth.email_form import EmailForm
from molb.views.auth.token import get_token_data
from molb.views.csrf_form import CsrfForm
from molb.views.send_message import send_confirmation
from molb.views.utils import _l
from molb.views.utils import flash
from molb.views.utils import generate_csrf_meta


@aiohttp_jinja2.template("auth/email-password.html")
async def handler(request):
    if request.method == "POST":
        form = EmailForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            data = dict(form.data.items())
            email_address = data["email_address"]
            async with request.app["db-pool"].acquire() as conn:
                q = "SELECT id, email_address FROM client WHERE email_address = $1"
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
                await send_confirmation(
                    request,
                    client["email_address"],
                    {"id": client["id"]},
                    "confirm_password",
                    _("Modification de mot de passe"),
                    "password-confirmation"
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


class PasswordForm(CsrfForm):
    password = PasswordField(
        _l("Mot de passe"),
        validators=[
            DataRequired(),
            EqualTo("password2", message=_l("Les mots de passe doivent être identiques")),
            Length(min=6)
        ],
        render_kw={"placeholder": _l("Entrez votre mot de passe")}
    )
    password2 = PasswordField(
        _l("Répétition du mot de passe"),
        validators=[DataRequired()],
        render_kw={"placeholder": _l("Répétez votre mot de passe")}
    )
    submit = SubmitField(_l("Valider"))


@aiohttp_jinja2.template("auth/password.html")
async def confirm(request):
    token = request.match_info["token"]
    try:
        token_data = get_token_data(
            token, request.app["config"]["application"]["secret_key"]
        )
        id_ = token_data["id"]
    except Exception:
        flash(request, ("danger", _("Le lien est invalide ou a expiré")))
        raise HTTPBadRequest()

    if request.method == "POST":
        form = PasswordForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            password_hash = sha256_crypt.hash(form.password.data)

            async with request.app["db-pool"].acquire() as conn:
                q = "UPDATE client SET password_hash = $1 WHERE id = $2"
                try:
                    await conn.execute(q, password_hash, id_)
                except Exception:
                    flash(
                        request,
                        (
                            "danger",
                            _("Votre mot de passe ne peut être modifié")
                        )
                    )
                    return {"form": form, "token": token}
                else:
                    flash(
                        request,
                        (
                            "info",
                            _(
                                "Votre mot de passe a été modifié, "
                                "vous pouvez vous connecter"
                            )
                        )
                    )
                    return HTTPFound(request.app.router["login"].url_for())
        else:
            flash(request, ("danger", _("Le formulaire contient des erreurs.")))
        return {"form": form, "token": token}
    elif request.method == "GET":
        form = PasswordForm(meta=await generate_csrf_meta(request))
        return {"form": form, "token": token}
    else:
        raise HTTPMethodNotAllowed()
