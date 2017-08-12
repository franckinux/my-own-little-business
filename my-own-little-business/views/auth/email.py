from aiohttp_jinja2 import get_env
from aiohttp.web import HTTPBadRequest
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_security import authorized_userid
from aiohttp_session_flash import flash
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from auth import require
from views.auth.email_form import EmailForm
from views.auth.send_message import SmtpSendingError
from views.auth.send_message import send_message
from views.auth.token import generate_token
from views.auth.token import get_token_data
from views.utils import generate_csrf_meta


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
            try:
                await send_confirmation(request, client["id"], email_address)
            except SmtpSendingError:
                flash(
                    request,
                    (
                        "danger",
                        "Le message de confirmation ne peut être envoyé à {}".format(
                            email_address
                        )
                    )
                )
            else:
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


async def send_confirmation(request, id_, email_address):
    config = request.app["config"]["application"]

    token = generate_token(config["secret_key"], id=id_, email_address=email_address)
    url = config["url"] + str(request.app.router["confirm_email"].url_for(token=token))

    env = get_env(request.app)
    template = env.get_template("auth/email-confirmation.txt")
    text_part = template.render(url=url)
    text_message = MIMEText(text_part, "plain")
    template = env.get_template("auth/email-confirmation.html")
    html_part = template.render(url=url)
    html_message = MIMEText(html_part, "html")

    message = MIMEMultipart("alternative")
    message["subject"] = "[{}] Changement d'adresse mail".format(config["site_name"])
    message["to"] = email_address
    message["from"] = config["from"]
    message.attach(text_message)
    message.attach(html_message)
    await send_message(message, config)
