from aiohttp.web import HTTPMethodNotAllowed
from aiohttp.web import HTTPFound
import aiohttp_jinja2
from aiohttp_session_flash import flash
from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.sql import delete
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from wtforms import BooleanField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import validators

from .csrf_form import CsrfForm
from .flash_messages import *
from model import Repository
from utils import generate_csrf_meta
from utils import remove_special_data


class RepositoryForm(CsrfForm):
    name = StringField("Name", [validators.Required(), validators.Length(min=6, max=128)])
    opened = BooleanField("Opened")
    submit = SubmitField("Submit")


@aiohttp_jinja2.template("create-repository.html")
async def create_repository(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        if request.method == "POST":
            form = RepositoryForm(await request.post(), meta=await generate_csrf_meta(request))
            if form.validate():
                q = insert(Repository).values(**remove_special_data(form.data.items()))
                try:
                    await conn.execute(q)
                except IntegrityError:
                    flash(request, (WARNING, "cannot create the repository"))
                    return {"form": form}
                flash(request, (SUCCESS, "repository successfuly created"))
                return {"form": form}
            else:
                flash(request, (ERROR, "there are some fields in error"))
                return {"form": form}
        else:  # GET !
            form = RepositoryForm(meta=await generate_csrf_meta(request))
            return {"form": form}


@aiohttp_jinja2.template("list-repository.html")
async def delete_repository(request):
    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Repository).where(Repository.__table__.c.id == id_)
        try:
            result = await conn.execute(q)
        except IntegrityError:
            flash(request, (WARNING, "cannot delete the repository"))
        else:
            flash(request, (SUCCESS, "repository successfuly deleted"))
        finally:
            result = await conn.execute(select([Repository]).order_by(Repository.__table__.c.name))
            rows = await result.fetchall()
            return {"repositories": rows}


@aiohttp_jinja2.template("edit-repository.html")
async def edit_repository(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = select([Repository], Repository.__table__.c.id == id_)
        result = await conn.execute(q)
        data = dict(await result.fetchone())
        if request.method == "POST":
            form = RepositoryForm(
                await request.post(),
                data=data,
                meta=await generate_csrf_meta(request)
            )
            if form.validate():
                q = update(Repository).where(
                    Repository.__table__.c.id == id_).values(**remove_special_data(form.data.items())
                    )
                try:
                    await conn.execute(q)
                except IntegrityError:
                    flash(request, (WARNING, "cannot edit the repository"))
                    return {"id": id_, "form": form}
                flash(request, (SUCCESS, "repository successfuly edited"))
                return {"id": id_, "form": form}
            else:
                flash(request, (ERROR, "there are some fields in error"))
                return {"id": id_, "form": form}
        else:  # GET !
            form = RepositoryForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": id_, "form": form}


@aiohttp_jinja2.template("list-repository.html")
async def list_repository(request):
    async with request.app["engine"].acquire() as conn:
        result = await conn.execute(select([Repository]).order_by(Repository.__table__.c.name))
        rows = await result.fetchall()
    return {"repositories": rows}
