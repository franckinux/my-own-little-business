from datetime import datetime

from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_security import forget
from aiohttp_security import remember
from aiohttp_session_flash import flash
from asyncpg.exceptions import UniqueViolationError
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

from auth import require
from auth.db_auth import check_credentials
from model import Client
from model import Repository
from views.auth.confirm import get_id_from_token
from views.auth.confirm import send_confirmation
from views.auth.confirm import SmtpSendingError
from views.csrf_form import CsrfForm
from views.utils import generate_csrf_meta
from views.utils import remove_special_data


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
async def register(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch(select([Repository]))
        repository_choices = [(row.id, row.name) for row in rows]

        if request.method == "POST":
            form = RegisterForm(await request.post(), meta=await generate_csrf_meta(request))
            form.repository_id.choices = repository_choices
            if form.validate():
                data = remove_special_data(form.data.items())
                email = data["email_address"]
                del data["password2"]
                data["password_hash"] = sha256_crypt.hash(data.pop("password"))
                try:
                    async with request.app["db-pool"].transaction() as conn:
                        q = insert(Client).values(**data).returning(literal_column('*'))
                        try:
                            client = await conn.fetchrow(q)
                        except UniqueViolationError:
                            flash(request, ("warning", "cannot create the client, it already exists"))
                            raise  # client not created
                        try:
                            await send_confirmation(request.app, client)
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
        q = update(Client).where(Client.__table__.c.id == id_).values(confirmed=True)
        try:
            await conn.fetchrow(q)
        except:
            flash(request, ("danger", "your account cannot be confirmed"))
            return
        else:
            flash(request, ("info", "your account has been confirmed, you can now login"))
            return HTTPFound(request.app.router["login"].url_for())
