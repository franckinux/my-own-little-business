from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_babel.middlewares import _
import aiohttp_jinja2
from aiohttp_security import forget
from aiohttp_security import remember
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import DataRequired

from molb.auth import require
from molb.auth.db_auth import check_credentials
from molb.views.csrf_form import CsrfForm
from molb.views.utils import _l
from molb.views.utils import flash
from molb.views.utils import generate_csrf_meta


class LoginForm(CsrfForm):
    login = StringField(
        _l("Identifiant"),
        validators=[DataRequired()],
        render_kw={"placeholder": _l("Entrez votre identifiant")}
    )
    password = PasswordField(
        _l("Mot de passe"),
        validators=[DataRequired()],
        render_kw={"placeholder": _l("Entrez votre mot de passe")}
    )
    submit = SubmitField(_l("Valider"))


@aiohttp_jinja2.template("auth/login.html")
async def login(request):
    if request.method == "POST":
        form = LoginForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            response = HTTPFound(request.app.router["home"].url_for())
            login = form.login.data
            password = form.password.data
            db_pool = request.app["db-pool"]
            if await check_credentials(db_pool, login, password):
                async with request.app["db-pool"].acquire() as conn:
                    q = (
                        "UPDATE client SET last_seen = NOW() WHERE login = $1 "
                        "RETURNING first_name, super_user"
                    )
                    client = await conn.fetchrow(q, login)
                await remember(request, response, login)
                if not client["super_user"]:
                    flash(
                        request,
                        (
                            "info",
                            _("Bonjour {} ! Ravi de vous revoir à nouveau").format(
                                client["first_name"])
                        )
                    )
                return response
        flash(request, ("danger", _("La combinaison identifiant/mot de passe est invalide")))
        return {"form": form}
    elif request.method == "GET":
        form = LoginForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


@require("client")
async def logout(request):
    response = HTTPFound(request.app.router["login"].url_for())
    await forget(request, response)
    flash(request, ("info", _("Vous êtes déconnecté")))
    return response


@require("admin")
async def switch(request):
    login = request.match_info["login"]
    response = HTTPFound(request.app.router["home"].url_for())
    await remember(request, response, login)
    return response
