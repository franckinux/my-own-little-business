from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import IntegrityConstraintViolationError
from sqlalchemy import select
from sqlalchemy.sql import delete
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from wtforms import BooleanField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Length
from wtforms.validators import Required

from auth import require
from .csrf_form import CsrfForm
from model import Repository
from views.utils import generate_csrf_meta
from views.utils import remove_special_data


class RepositoryForm(CsrfForm):
    name = StringField("Name", validators=[Required(), Length(min=6, max=128)])
    opened = BooleanField("Opened")
    submit = SubmitField("Submit")


@require("admin")
@aiohttp_jinja2.template("create-repository.html")
async def create_repository(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    if request.method == "POST":
        form = RepositoryForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            async with request.app["db-pool"].acquire() as conn:
                q = insert(Repository).values(**remove_special_data(form.data.items()))
                try:
                    await conn.execute(q)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot create the repository"))
                    return {"form": form}
            flash(request, ("success", "repository successfuly created"))
            return {"form": form}
        else:
            flash(request, ("danger", "there are some fields in error"))
            return {"form": form}
    else:  # GET !
        form = RepositoryForm(meta=await generate_csrf_meta(request))
        return {"form": form}


@require("admin")
@aiohttp_jinja2.template("list-repository.html")
async def delete_repository(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Repository).where(Repository.__table__.c.id == id_)
        try:
            await conn.execute(q)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", "cannot delete the repository"))
        else:
            flash(request, ("success", "repository successfuly deleted"))
        finally:
            rows = await conn.fetch(select([Repository]).order_by(Repository.__table__.c.name))
            return {"repositories": rows}


@require("admin")
@aiohttp_jinja2.template("edit-repository.html")
async def edit_repository(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    id_ = int(request.match_info["id"])
    q = select([Repository], Repository.__table__.c.id == id_)
    data = dict(await conn.fetchrow(q))
    if request.method == "POST":
        form = RepositoryForm(
            await request.post(),
            data=data,
            meta=await generate_csrf_meta(request)
        )
        if form.validate():
            async with request.app["db-pool"].acquire() as conn:
                q = update(Repository).where(
                    Repository.__table__.c.id == id_).values(**remove_special_data(form.data.items())
                )
                try:
                    await conn.execute(q)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot edit the repository"))
                else:
                    flash(request, ("success", "repository successfuly edited"))
            return {"id": id_, "form": form}
        else:
            flash(request, ("danger", "there are some fields in error"))
            return {"id": id_, "form": form}
    else:  # GET !
        form = RepositoryForm(data=data, meta=await generate_csrf_meta(request))
        return {"id": id_, "form": form}


@require("admin")
@aiohttp_jinja2.template("list-repository.html")
async def list_repository(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch(select([Repository]).order_by(Repository.__table__.c.name))
    return {"repositories": rows}
