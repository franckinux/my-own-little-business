from aiohttp.web import HTTPMethodNotAllowed
from aiohttp.web import HTTPFound
import aiohttp_jinja2
from aiohttp_session_flash import flash
from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.sql import delete
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from sqlalchemy.sql.expression import desc
from wtforms import BooleanField
from wtforms import HiddenField
from wtforms import IntegerField
from wtforms import SubmitField
from wtforms import validators

from .csrf_form import CsrfForm
from .flash_messages import *
from model import Batch
from utils import generate_csrf_meta
from utils import remove_special_data


class BatchForm(CsrfForm):
    date = HiddenField("Date", [validators.Required()])
    capacity = IntegerField("Capacity", [validators.Required()])
    opened = BooleanField("Opened")
    submit = SubmitField("Submit")


@aiohttp_jinja2.template("create-batch.html")
async def create_batch(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["db-engine"].acquire() as conn:
        if request.method == "POST":
            form = BatchForm(await request.post(), meta=await generate_csrf_meta(request))
            if form.validate():
                q = insert(Batch).values(**remove_special_data(form.data.items()))
                try:
                    await conn.execute(q)
                except IntegrityError:
                    flash(request, (WARNING, "cannot create the batch"))
                    return {"form": form}
                flash(request, (SUCCESS, "batch successfuly created"))
                return {"form": form}
            else:
                flash(request, (ERROR, "there are some fields in error"))
                return {"form": form}
        else:  # GET !
            form = BatchForm(meta=await generate_csrf_meta(request))
            return {"form": form}


@aiohttp_jinja2.template("list-batch.html")
async def delete_batch(request):
    async with request.app["db-engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Batch).where(Batch.__table__.c.id == id_)
        try:
            result = await conn.execute(q)
        except IntegrityError:
            flash(request, (WARNING, "cannot delete the batch"))
        else:
            flash(request, (SUCCESS, "batch successfuly deleted"))
        finally:
            result = await conn.execute(select([Batch]).limit(30).order_by(desc(Batch.__table__.c.date)))
            rows = await result.fetchall()
            return {"batches": rows}


@aiohttp_jinja2.template("edit-batch.html")
async def edit_batch(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["db-engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = select([Batch], Batch.__table__.c.id == id_)
        result = await conn.execute(q)
        data = dict(await result.fetchone())
        if request.method == "POST":
            form = BatchForm(
                await request.post(),
                data=data,
                meta=await generate_csrf_meta(request)
            )
            if form.validate():
                q = update(Batch).where(
                    Batch.__table__.c.id == id_).values(**remove_special_data(form.data.items())
                    )
                try:
                    await conn.execute(q)
                except IntegrityError:
                    flash(request, (WARNING, "cannot edit the batch"))
                    return {"id": id_, "form": form}
                flash(request, (SUCCESS, "successfuly edited"))
                return {"id": id_, "form": form}
            else:
                flash(request, (ERROR, "there are some fields in error"))
                return {"id": id_, "form": form}
        else:  # GET !
            form = BatchForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": id_, "form": form}


@aiohttp_jinja2.template("list-batch.html")
async def list_batch(request):
    async with request.app["db-engine"].acquire() as conn:
        result = await conn.execute(select([Batch]).limit(30).order_by(desc(Batch.__table__.c.date)))
        rows = await result.fetchall()
    return {"batches": rows}
