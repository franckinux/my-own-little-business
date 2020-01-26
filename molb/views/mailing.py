from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_babel.middlewares import _
from wtforms import BooleanField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import TextAreaField
from wtforms.validators import Required

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.send_message import send_mailing_message
from molb.views.send_message import send_text_message
from molb.views.utils import _l
from molb.views.utils import flash
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data


class MailingForm(CsrfForm):
    all_repositories = BooleanField(_l("Tous les points de livraison"), default=True)
    repository_id = SelectField(_l("Point de livraison"), coerce=int)
    subject = StringField(_l("Sujet"), validators=[Required()])
    message = TextAreaField(_l("Message"), render_kw={"rows": 10, "cols": 50}, validators=[Required()])
    submit = SubmitField(_l("Valider"))


@require("admin")
@aiohttp_jinja2.template("mailing.html")
async def mailing(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch("SELECT id, name FROM repository WHERE opened")
        repository_choices = [(row["id"], row["name"]) for row in rows]

        if request.method == "POST":
            form = MailingForm(await request.post(), meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
            if form.validate():
                data = remove_special_data(form.data)
                subject = data["subject"]
                message = data["message"]
                if data["all_repositories"]:
                    q = (
                        "SELECT first_name, email_address FROM client "
                        "WHERE confirmed AND mailing"
                        )
                    rows = await conn.fetch(q)
                else:
                    repository_id = data.get("repository_id")
                    q = (
                        "SELECT first_name, email_address FROM client "
                        "WHERE confirmed AND mailing AND repository_id = $1"
                    )
                    rows = await conn.fetch(q, repository_id)
                if not rows:
                    flash(request, ("warning", _("Il n'y a pas de destinataire.")))
                    return HTTPFound(request.app.router["mailing"].url_for())

                if "<first_name>" in message:
                    for r in rows:
                        message_ = message.replace("<first_name>", r["first_name"])
                        await send_text_message(request, r["email_address"], subject, message_)
                else:
                    email_addresses = [r["email_address"] for r in rows]
                    await send_mailing_message(request, email_addresses, subject, message)
                flash(request, ("info", _("Les messages ont été envoyés.")))
                return HTTPFound(request.app.router["mailing"].url_for())
            else:
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
                return HTTPFound(request.app.router["mailing"].url_for())

        elif request.method == "GET":
            form = MailingForm(meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
            return {"form": form}

        else:
            raise HTTPMethodNotAllowed()
