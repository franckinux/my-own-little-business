from aiohttp.web import HTTPFound, HTTPUnauthorized
import aiohttp_jinja2
from aiohttp_security import remember, forget
from aiohttp_session_flash import flash
from wtforms import StringField
from wtforms import PasswordField
from wtforms import SubmitField
from wtforms import validators

from auth.db_auth import check_credentials
from auth.decorators import require
from .csrf_form import CsrfForm
from views.utils import generate_csrf_meta
# from views.utils import remove_special_data


class LoginForm(CsrfForm):
    login = StringField("Login", [validators.Required()])
    password = PasswordField("Capacity", [validators.Required()])
    submit = SubmitField("Submit")


@aiohttp_jinja2.template("login.html")
async def login(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    if request.method == "POST":
        form = LoginForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            response = HTTPFound('/client/')
            login = form.login.data
            password = form.password.data
            db_engine = request.app["db-engine"]
            if await check_credentials(db_engine, login, password):
                await remember(request, response, login)
                return response
        flash(request, ("danger", "Invalid username/password combination"))
    else:  # GET !
        form = LoginForm(meta=await generate_csrf_meta(request))
    return {"form": form}


@require("client")
async def logout(request):
    response = HTTPFound('/')
    await forget(request, response)
    flash(request, ("info", "You have been logged out"))
    return response
