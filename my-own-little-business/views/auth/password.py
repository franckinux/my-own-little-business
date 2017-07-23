from aiohttp_jinja2 import get_env
from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from passlib.hash import sha256_crypt
from wtforms import PasswordField
from wtforms import SubmitField
from wtforms.validators import EqualTo
from wtforms.validators import Length
from wtforms.validators import Required

from views.auth.email_form import EmailForm
from views.auth.send_message import SmtpSendingError
from views.auth.send_message import send_message
from views.auth.token import generate_token
from views.auth.token import get_token_data
from views.csrf_form import CsrfForm
from views.utils import generate_csrf_meta


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
                flash(request, ("danger", "there is no client corresponding to this email address"))
            else:
                try:
                    await send_confirmation(request, client["id"], client["email_address"])
                except SmtpSendingError:
                    flash(
                        request,
                        (
                            "danger",
                            "a problem occurred while sending a confirmation email to {]".format(
                                email_address
                            )
                        )
                    )
                else:
                    flash(
                        request,
                        (
                            "info",
                            "a confirmation email has been sent to {}, read it carefully".format(
                                email_address
                            )
                        )
                    )
                return HTTPFound(request.app.router["login"].url_for())
        else:
            flash(request, ("danger", "there are some fields in error"))
        return {"form": form}
    elif request.method == "GET":
        form = EmailForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


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
    token = request.match_info["token"]
    try:
        token_data = get_token_data(token, request.app["config"]["application"]["secret_key"])
        id_ = token_data["id"]
    except:
        flash(request, ("danger", "the link is invalid or has expired"))
        raise HTTPBadRequest()

    if request.method == "POST":
        form = PasswordForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            password_hash = sha256_crypt.hash(form.password.data)

            async with request.app["db-pool"].acquire() as conn:
                q = "UPDATE client SET password_hash = $1 WHERE id = $2 AND NOT disabled"
                try:
                    await conn.execute(q, password_hash, id_)
                except:
                    flash(request, ("danger", "your password cannot be recovered"))
                    return {"form": form, "token": token}
                else:
                    flash(request, ("info", "your password has been updated, you can now login"))
                    return HTTPFound(request.app.router["login"].url_for())
        else:
            flash(request, ("danger", "there are some fields in error"))
        return {"form": form, "token": token}
    elif request.method == "GET":
        form = PasswordForm(meta=await generate_csrf_meta(request))
        return {"form": form, "token": token}
    else:
        raise HTTPMethodNotAllowed()


async def send_confirmation(request, id_, email_address):
    config = request.app["config"]["application"]

    token = generate_token(config["secret_key"], id=id_)
    url = config["url"] + str(request.app.router["confirm_password"].url_for(token=token))

    env = get_env(request.app)
    template = env.get_template("auth/password-confirmation.txt")
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/password-confirmation.html")
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "[{}] Password recovery".format(config["site_name"])
    message["to"] = email_address
    message["from"] = config["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send_message(message, config)
