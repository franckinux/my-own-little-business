from aiohttp_jinja2 import get_env
from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import UniqueViolationError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from passlib.hash import sha256_crypt
from wtforms import PasswordField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Email
from wtforms.validators import EqualTo
from wtforms.validators import Length
from wtforms.validators import Regexp
from wtforms.validators import Required

from views.auth.send_message import SmtpSendingError
from views.auth.send_message import send_message
from views.auth.token import generate_token
from views.auth.token import get_token_data
from views.csrf_form import CsrfForm
from views.utils import field_list
from views.utils import generate_csrf_meta
from views.utils import place_holders
from views.utils import remove_special_data


class RegisterForm(CsrfForm):
    login = StringField("Identifiant", validators=[
        Required(),
        Length(min=1, max=64),
        Regexp("^[A-Za-z][A-Za-z0-9_.]*$", 0,
            "L'identifiant ne doit comporter que des lettres non accentuées, "
            "des chiffres, '.'  et '_' et commencer par une lettre"
        )
    ])
    password = PasswordField("Mot de passe", validators=[
        Required(),
        EqualTo("password2", message="Passwords must match"),
        Length(min=6)
    ])
    password2 = PasswordField("Répétition du mot de passe", validators=[Required()])
    first_name = StringField("Prénom")
    last_name = StringField("Nom")
    email_address = StringField("Adresse mail", validators=[
        Required(),
        Length(min=1, max=64),
        Email()
    ])
    phone_number = StringField("Numéro de téléphone", validators=[
        Regexp("^(0|\+33)[1-9]([-. ]?[0-9]{2}){4}$", 0)
    ])
    repository_id = SelectField("Point de livraison", coerce=int)
    submit = SubmitField("Soumettre")


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
                                    (
                                        "Votre compte ne peut être créé, cet "
                                        "identifiant est déjà utilisé"
                                    )
                                )
                            )
                            raise  # rollback the transaction : client not created
                        try:
                            await send_confirmation(request, client["id"], client["email_address"])
                        except SmtpSendingError:
                            flash(
                                request,
                                (
                                    "danger",
                                    "Le message de confirmation n'a pu être envoyé à {}".format(
                                        client["email_address"]
                                    )
                                )
                            )
                            raise  # rollback the transaction : client not created
                        flash(
                            request,
                            (
                                "info",
                                "Un message de confirmation a été envoyé à {}".format(
                                    client["email_address"]
                                )
                            )
                        )
                        return HTTPFound(request.app.router["login"].url_for())
                except (UniqueViolationError, SmtpSendingError):
                    return HTTPFound(request.app.router["register"].url_for())
            else:
                flash(request, ("danger", "Le formulaire comporte des erreurs"))
            return {"form": form}
        elif request.method == "GET":
            form = RegisterForm(meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
            return {"form": form}
        else:
            raise HTTPMethodNotAllowed()


@aiohttp_jinja2.template("auth/confirmation.html")
async def confirm(request):
    token = request.match_info["token"]

    try:
        token_data = get_token_data(token, request.app["config"]["application"]["secret_key"])
        id_ = token_data["id"]
    except:
        flash(request, ("danger", "Le lien est invalide ou a expiré"))
        raise HTTPBadRequest()

    async with request.app["db-pool"].acquire() as conn:
        q = "UPDATE client SET confirmed = true WHERE id = $1"
        try:
            await conn.execute(q, id_)
        except:
            flash(request, ("danger", "Vous ne pouvez pas être enregistré"))
            return HTTPFound(request.app.router["register"].url_for())
        else:
            flash(request, ("info", "Votre enregistrement est confirmé, vous pouvez vous connecter"))
            return HTTPFound(request.app.router["login"].url_for())


async def send_confirmation(request, id_, email_address):
    config = request.app["config"]["application"]

    token = generate_token(config["secret_key"], id=id_)
    url = config["url"] + str(request.app.router["confirm_register"].url_for(token=token))

    env = get_env(request.app)
    template = env.get_template("auth/register-confirmation.txt")
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/register-confirmation.html")
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "[{}] Confirmation de votre enregistrement".format(config["site_name"])
    message["to"] = email_address
    message["from"] = config["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send_message(message, config)
