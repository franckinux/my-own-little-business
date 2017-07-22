from aiohttp_jinja2 import get_env
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
from views.auth.token import generate_confirmation_token
from views.auth.token import get_id_from_token
from views.csrf_form import CsrfForm
from views.utils import field_list
from views.utils import generate_csrf_meta
from views.utils import place_holders
from views.utils import remove_special_data
from views.utils import settings


class RegisterForm(CsrfForm):
    login = StringField("Login", validators=[
        Required(),
        Length(min=1, max=64),
        Regexp("^[A-Za-z][A-Za-z0-9_.]*$", 0,
            "Login must have only letters, numbers, dots or underscores"
            "and begin by a letter"
        )
    ])
    password = PasswordField("Password", validators=[
        Required(),
        EqualTo("password2", message="Passwords must match"),
        Length(min=6)
    ])
    password2 = PasswordField("Confirm password", validators=[Required()])
    first_name = StringField("First name")
    last_name = StringField("Last name")
    email_address = StringField("Email address", validators=[
        Required(),
        Length(min=1, max=64),
        Email()
    ])
    phone_number = StringField("Phone number", validators=[
        Regexp("^(0|\+33)[1-9]([-. ]?[0-9]{2}){4}$", 0)
    ])
    repository_id = SelectField("Repository", coerce=int)
    submit = SubmitField("Submit")


@aiohttp_jinja2.template("auth/register.html")
async def handler(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch("SELECT id, name FROM repository")
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
                            flash(request, ("warning", "cannot create the client, it already exists"))
                            raise  # client not created
                        try:
                            await send_confirmation(request, client)
                        except SmtpSendingError:
                            flash(request, ("danger", "a problem occurred while sending a confirmation email to you"))
                            raise  # rollback the transaction : client not created
                        flash(request, ("info", "a confirmation email has been sent to you, read it carefully"))
                except (UniqueViolationError, SmtpSendingError):
                    pass
            else:
                flash(request, ("danger", "there are some fields in error"))
        else:  # GET !
            form = RegisterForm(meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
    return {"form": form}


@aiohttp_jinja2.template("auth/confirmation.html")
async def confirm(request):
    token = request.match_info["token"]

    try:
        id_ = get_id_from_token(token, request.app["config"]["application"]["secret_key"])
    except:
        flash(request, ("danger", "your account cannot be confirmed"))
        return

    async with request.app["db-pool"].acquire() as conn:
        q = "UPDATE client SET confirmed = true WHERE id = $1"
        try:
            await conn.execute(q, id_)
        except:
            flash(request, ("danger", "your account cannot be confirmed"))
            return
        else:
            flash(request, ("info", "your account has been confirmed, you can now login"))
            return HTTPFound(request.app.router["login"].url_for())


async def send_confirmation(request, client):
    config = request.app["config"]["application"]

    token = generate_confirmation_token(client["id"], config["secret_key"])
    url = config["url"] + str(request.app.router["confirm_register"].url_for(token=token))

    env = get_env(request.app)
    template = env.get_template("auth/register-confirmation.txt")
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/register-confirmation.html")
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "Confirm your account"
    message["to"] = client["email_address"]
    message["from"] = config["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send_message(message, config)
