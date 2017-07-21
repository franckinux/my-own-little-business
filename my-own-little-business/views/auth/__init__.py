from datetime import datetime

from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_security import forget
from aiohttp_security import remember
from aiohttp_session_flash import flash
from sqlalchemy.sql import update
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Required

from auth import require
from auth.db_auth import check_credentials
from model import Client
from views.csrf_form import CsrfForm
from views.utils import generate_csrf_meta


class LoginForm(CsrfForm):
    login = StringField("Login", [Required()])
    password = PasswordField("Password", [Required()])
    submit = SubmitField("Submit")


@aiohttp_jinja2.template("auth/login.html")
async def login(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    if request.method == "POST":
        form = LoginForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            response = HTTPFound(request.app.router["client"].url_for())
            login = form.login.data
            password = form.password.data
            db_pool = request.app["db-pool"]
            if await check_credentials(db_pool, login, password):
                async with request.app["db-pool"].acquire() as conn:
                    q = update(Client).where(
                        Client.__table__.c.login == login).values(last_seen=datetime.utcnow()
                    )
                    await conn.fetchrow(q)
                await remember(request, response, login)
                return response
        flash(request, ("danger", "Invalid username/password combination"))
    else:  # GET !
        form = LoginForm(meta=await generate_csrf_meta(request))
    return {"form": form}


@require("client")
async def logout(request):
    response = HTTPFound(request.app.router["login"].url_for())
    await forget(request, response)
    flash(request, ("info", "You have been logged out"))
    return response
