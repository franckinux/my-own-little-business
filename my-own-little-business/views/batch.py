from aiohttp.web import HTTPMethodNotAllowed
from aiohttp.web import HTTPFound
import aiohttp_jinja2
from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.sql import delete
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from sqlalchemy.sql.expression import desc
from wtforms import Form
from wtforms import BooleanField
# from wtforms import DateTimeField
from wtforms import HiddenField
from wtforms import IntegerField
from wtforms import validators

from model import Batch


class BatchForm(Form):
    # date = DateTimeField("Date", [validators.Required()], format="%Y-%m-%d", type="hidden", value="")
    date = HiddenField("Date", [validators.Required()])
    capacity = IntegerField("Capacity", [validators.Required()])
    opened = BooleanField("Opened")


@aiohttp_jinja2.template("create-batch.html")
async def create_batch(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        if request.method == "POST":
            form = BatchForm(await request.post())
            if form.validate():
                q = insert(Batch).values(**dict(form.data.items()))
                try:
                    await conn.execute(q)
                except IntegrityError as e:
                    message = "cannot create the batch"
                    return {"form": form, "warning_message": message}
                message = "batch successfuly created"
                return {"form": form, "success_message": message}
            else:
                message = "there are some fields in error"
                return {"form": form, "warning_message": message}
        else:  # GET !
            form = BatchForm()
            return {"form": form}


@aiohttp_jinja2.template("list-batch.html")
async def delete_batch(request):
    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Batch).where(Batch.__table__.c.id == id_)
        ok = False
        try:
            result = await conn.execute(q)
            message = "successfuly deleted"
            ok = True
        except IntegrityError:
            message = "cannot delete batch"
        finally:
            result = await conn.execute(select([Batch]).limit(30).order_by(desc(Batch.__table__.c.date)))
            rows = await result.fetchall()
            if ok:
                return {"batches": rows, "success_message": message}
            else:
                return {"batches": rows, "warning_message": message}


@aiohttp_jinja2.template("edit-batch.html")
async def edit_batch(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = select([Batch], Batch.__table__.c.id == id_)
        result = await conn.execute(q)
        data = dict(await result.fetchone())
        if request.method == "POST":
            form = BatchForm(await request.post(), data=data)
            if form.validate():
                q = update(Batch).where(
                    Batch.__table__.c.id == id_).values(**dict(form.data.items())
                    )
                try:
                    await conn.execute(q)
                except IntegrityError:
                    message = "cannot edit the batch"
                    return {"id": id_, "form": form, "warning_message": message}
                message = "batch successfuly edited"
                return {"id": id_, "form": form, "success_message": message}
            else:
                message = "there are some fields in error"
                return {"id": id_, "form": form, "warning_message": message}
        else:  # GET !
            form = BatchForm(data=data)
            return {"id": id_, "form": form}


@aiohttp_jinja2.template("list-batch.html")
async def list_batch(request):
    async with request.app["engine"].acquire() as conn:
        result = await conn.execute(select([Batch]).limit(30).order_by(desc(Batch.__table__.c.date)))
        rows = await result.fetchall()
    return {"batches": rows}
