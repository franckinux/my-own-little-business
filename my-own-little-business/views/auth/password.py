from aiohttp_jinja2 import get_env
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import UniqueViolationError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from passlib.hash import sha256_crypt
from sqlalchemy import literal_column
from sqlalchemy import select
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from wtforms import PasswordField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Email
from wtforms.validators import EqualTo
from wtforms.validators import Length
from wtforms.validators import Regexp
from wtforms.validators import Required

from model import Client
from model import Repository
from views.auth.send_message import SmtpSendingError
from views.auth.send_message import send_message
from views.auth.token import generate_confirmation_token
from views.auth.token import get_id_from_token
from views.csrf_form import CsrfForm
from views.utils import generate_csrf_meta


class EmailForm(CsrfForm):
    email_address = StringField("Email address", validators=[
        Required(),
        Length(min=1, max=64),
        Email()
    ])
    submit = SubmitField("Submit")



@aiohttp_jinja2.template("auth/email.html")
async def handler(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    if request.method == "POST":
        form = EmailForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            data = dict(form.data.items())
            email = data["email_address"]
            async with request.app["db-pool"].acquire() as conn:
                q = select([Client]).where(Client.__table__.c.email_address == email)
                client = await conn.fetchrow(q)
            if client.row is None:
                flash(request, ("danger", "there is no client corresponding to this email address"))
            else:
                try:
                    await send_confirmation(request, client)
                except SmtpSendingError:
                    flash(request, ("danger", "a problem occurred while sending a confirmation email to you"))
                flash(request, ("info", "a confirmation email has been sent to you, read it carefully"))
        else:
            flash(request, ("danger", "there are some fields in error"))
    else:  # GET !
        form = EmailForm(meta=await generate_csrf_meta(request))
    return {"form": form}


class PasswordForm(CsrfForm):
    password = PasswordField("Password", validators=[
        Required(),
        EqualTo("password2", message="Passwords must match"),
        Length(min=6)
    ])
    password2 = PasswordField("Confirm password", validators=[Required()])
    submit = SubmitField("Submit")


@aiohttp_jinja2.template("auth/password.html")
async def confirm(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    token = request.match_info["token"]

    try:
        id_ = get_id_from_token(token, request.app["config"]["application"]["secret_key"])
    except:
        flash(request, ("danger", "password recovery cannot recovered"))
        return

    if request.method == "POST":
        import pdb; pdb.set_trace()
        form = PasswordForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            password_hash = sha256_crypt.hash(form.password.data)

            async with request.app["db-pool"].acquire() as conn:
                # TODO : AND client not disabled
                q = update(Client).where(Client.__table__.c.id ==
                                         id_).values(password_hash=password_hash)
                try:
                    await conn.fetchrow(q)
                except:
                    flash(request, ("danger", "your password cannot be recovered"))
                    return
                else:
                    flash(request, ("info", "your password has been updated, you can now login"))
                    return HTTPFound(request.app.router["login"].url_for())
        else:
            flash(request, ("danger", "there are some fields in error"))
    else:  # GET !
        form = PasswordForm(meta=await generate_csrf_meta(request))
    return {"form": form, "token": token}



async def send_confirmation(request, client):
    config = request.app["config"]["application"]

    token = generate_confirmation_token(client.id, config["secret_key"])
    url = config["url"] + request.app.router["confirm_password"].url_for(token=token)

    env = get_env(request.app)
    template = env.get_template("auth/password-confirmation.txt")
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/password-confirmation.html")
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "Password recovery"
    message["to"] = client.email_address
    message["from"] = config["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send_message(message, config)
