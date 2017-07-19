from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import IntegrityConstraintViolationError
from sqlalchemy import select
from sqlalchemy.sql import delete
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from sqlalchemy.sql.expression import desc
from wtforms import BooleanField
from wtforms import DateTimeField
from wtforms import IntegerField
from wtforms import SubmitField
from wtforms.validators import Required

from auth import require
from .csrf_form import CsrfForm
from model import Batch
from views.utils import generate_csrf_meta
from views.utils import remove_special_data


class BatchForm(CsrfForm):
    date = DateTimeField("Date", validators=[Required()])
    capacity = IntegerField("Capacity", validators=[Required()])
    opened = BooleanField("Opened")
    submit = SubmitField("Submit")


@require("admin")
@aiohttp_jinja2.template("create-batch.html")
async def create_batch(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    if request.method == "POST":
        form = BatchForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            async with request.app["db-pool"].acquire() as conn:
                q = insert(Batch).values(**remove_special_data(form.data.items()))
                try:
                    await conn.fetchrow(q)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot create the batch"))
                    return {"form": form}
            flash(request, ("success", "batch successfuly created"))
            return {"form": form}
        else:
            flash(request, ("danger", "there are some fields in error"))
            return {"form": form}
    else:  # GET !
        form = BatchForm(meta=await generate_csrf_meta(request))
        return {"form": form}


@require("admin")
@aiohttp_jinja2.template("list-batch.html")
async def delete_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Batch).where(Batch.__table__.c.id == id_)
        try:
            await conn.fetchrow(q)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", "cannot delete the batch"))
        else:
            flash(request, ("success", "batch successfuly deleted"))
        finally:
            rows = await conn.fetch(select([Batch]).limit(30).order_by(desc(Batch.__table__.c.date)))
            return {"batches": rows}


@require("admin")
@aiohttp_jinja2.template("edit-batch.html")
async def edit_batch(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    id_ = int(request.match_info["id"])
    q = select([Batch], Batch.__table__.c.id == id_)
    data = dict(await conn.fetchrow(q))
    if request.method == "POST":
        form = BatchForm(
            await request.post(),
            data=data,
            meta=await generate_csrf_meta(request)
        )
        if form.validate():
            async with request.app["db-pool"].acquire() as conn:
                q = update(Batch).where(
                    Batch.__table__.c.id == id_).values(**remove_special_data(form.data.items())
                )
                try:
                    await conn.fetchrow(q)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot edit the batch"))
                else:
                    flash(request, ("success", "successfuly edited"))
            return {"id": id_, "form": form}
        else:
            flash(request, ("danger", "there are some fields in error"))
            return {"id": id_, "form": form}
    else:  # GET !
        form = BatchForm(data=data, meta=await generate_csrf_meta(request))
        return {"id": id_, "form": form}


@require("admin")
@aiohttp_jinja2.template("list-batch.html")
async def list_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch(select([Batch]).limit(30).order_by(desc(Batch.__table__.c.date)))
    return {"batches": rows}
