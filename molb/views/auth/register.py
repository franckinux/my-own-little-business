from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_babel.middlewares import _
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import UniqueViolationError
from passlib.hash import sha256_crypt
from wtforms import BooleanField
from wtforms import PasswordField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Email
from wtforms.validators import EqualTo
from wtforms.validators import Length
from wtforms.validators import Regexp
from wtforms.validators import Required

from molb.views.auth.token import get_token_data
from molb.views.csrf_form import CsrfForm
from molb.views.send_message import send_confirmation
from molb.views.utils import _l
from molb.views.utils import field_list
from molb.views.utils import generate_csrf_meta
from molb.views.utils import place_holders
from molb.views.utils import remove_special_data


class RegisterForm(CsrfForm):
    login = StringField(
        _l("Identifiant"),
        validators=[
            Required(),
            Length(min=1, max=64),
            Regexp("^[A-Za-z][A-Za-z0-9_.]*$", 0,
                _l("L'identifiant ne doit contenir que des lettres non accentuées, "
                "des chiffres, '.'  et '_' et commencer par une lettre"))
        ],
        render_kw={"placeholder": _l("Entrez votre identifiant")}
    )
    password = PasswordField(
        _l("Mot de passe"),
        validators=[
            Required(),
            EqualTo("password2", message=_l("Les mots de passe doivent être identiques")),
            Length(min=6)
        ],
        render_kw={"placeholder": _l("Entrez votre mot de passe")}
    )
    password2 = PasswordField(
        _l("Répétition du mot de passe"),
        validators=[Required()],
        render_kw={"placeholder": _l("Répétez votre mot de passe")}
    )
    first_name = StringField(
        _l("Prénom"),
        render_kw={"placeholder": _l("Entrez votre prénom")}
    )
    last_name = StringField(
        _l("Nom"),
        render_kw={"placeholder": _l("Entrez votre nom")}
    )
    email_address = StringField(
        _l("Adresse email"),
        validators=[
            Required(),
            Length(min=1, max=64),
            Email()
        ],
        render_kw={"placeholder": _l("Entrez votre adresse email")}
    )
    phone_number = StringField(
        _l("Numéro de téléphone"),
        validators=[
            Regexp("^(0|\+33)[1-9]([-. ]?[0-9]{2}){4}$", 0)
        ],
        render_kw={"placeholder": _l("Entrez votre numéro de téléphone")}
    )
    repository_id = SelectField(_l("Point de livraison"), coerce=int)
    mailing = BooleanField(_l("Réception de messages"), default=True)
    submit = SubmitField(_l("Valider"))


@aiohttp_jinja2.template("auth/register.html")
async def handler(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch("SELECT id, name FROM repository WHERE opened")
        repository_choices = [(row["id"], row["name"]) for row in rows]

        if request.method == "POST":
            form = RegisterForm(await request.post(), meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
            if form.validate():
                data = remove_special_data(form.data.items())
                del data["password2"]
                data["password_hash"] = sha256_crypt.hash(data.pop("password"))
                try:
                    async with conn.transaction():
                        q = "INSERT INTO client ({}) VALUES ({}) RETURNING *".format(
                            field_list(data), place_holders(data)
                        )
                        try:
                            client = await conn.fetchrow(q, *data.values())
                        except UniqueViolationError:
                            flash(
                                request,
                                (
                                    "warning",
                                    _(
                                        "Votre profil ne peut être créé, cet "
                                        "identifiant est déjà utilisé"
                                    )
                                )
                            )
                            raise  # rollback the transaction : client not created
                        await send_confirmation(
                            request,
                            client["email_address"],
                            {"id": client["id"]},
                            "confirm_register",
                            _("Confirmation de votre enregistrement"),
                            "register-confirmation"
                        )
                        flash(
                            request,
                            (
                                "info",
                                _("Un email de confirmation a été envoyé à {}").format(
                                    client["email_address"]
                                )
                            )
                        )
                        return HTTPFound(request.app.router["login"].url_for())
                except Exception:
                    return HTTPFound(request.app.router["register"].url_for())
            else:
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
            return {"form": form}
        elif request.method == "GET":
            form = RegisterForm(meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
            return {"form": form}
        else:
            raise HTTPMethodNotAllowed()


async def confirm(request):
    token = request.match_info["token"]

    try:
        token_data = get_token_data(token, request.app["config"]["application"]["secret_key"])
        id_ = token_data["id"]
    except Exception:
        flash(request, ("danger", _("Le lien est invalide ou a expiré")))
        raise HTTPBadRequest()

    async with request.app["db-pool"].acquire() as conn:
        q = "UPDATE client SET confirmed = true WHERE id = $1 RETURNING id"
        try:
            updated = await conn.fetchval(q, id_)
            if updated is None:
                raise
        except Exception:
            flash(request, ("danger", _("Vous ne pouvez pas être enregistré.")))
            return HTTPFound(request.app.router["register"].url_for())
        else:
            flash(
                request,
                (
                    "info",
                    _("Votre enregistrement est confirmé, vous pouvez vous connecter.")
                )
            )
            return HTTPFound(request.app.router["login"].url_for())
