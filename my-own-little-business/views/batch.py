from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import IntegrityConstraintViolationError
from wtforms import BooleanField
from wtforms import DateTimeField
from wtforms import IntegerField
from wtforms import SubmitField
from wtforms.validators import Required

from auth import require
from .csrf_form import CsrfForm
from views.utils import field_list
from views.utils import generate_csrf_meta
from views.utils import place_holders
from views.utils import remove_special_data
from views.utils import settings


class BatchForm(CsrfForm):
    date = DateTimeField("Date", validators=[Required()])
    capacity = IntegerField("Capacity", validators=[Required()])
    opened = BooleanField("Opened")
    submit = SubmitField("Submit")


@require("admin")
@aiohttp_jinja2.template("create-batch.html")
async def create_batch(request):
    if request.method == "POST":
        form = BatchForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            data = remove_special_data(form.data.items())
            async with request.app["db-pool"].acquire() as conn:
                q = "INSERT INTO batch ({}) VALUES ({})".format(
                    field_list(data), place_holders(data)
                )
                try:
                    await conn.execute(q, *data.values())
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot create the batch"))
                    return {"form": form}
            flash(request, ("success", "batch successfuly created"))
            return HTTPFound(request.app.router["list_batch"].url_for())
        else:
            flash(request, ("danger", "there are some fields in error"))
            return {"form": form}
    elif request.method == "GET":
        form = BatchForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


@require("admin")
async def delete_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        try:
            await conn.execute("DELETE FROM batch WHERE id = $1", id_)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", "cannot delete the batch"))
        else:
            flash(request, ("success", "batch successfuly deleted"))
        finally:
            return HTTPFound(request.app.router["list_batch"].url_for())


@require("admin")
@aiohttp_jinja2.template("edit-batch.html")
async def edit_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        data = dict(await conn.fetchrow("SELECT * FROM batch WHERE id = $1", id_))
        if request.method == "POST":
            form = BatchForm(
                await request.post(),
                data=data,
                meta=await generate_csrf_meta(request)
            )
            if form.validate():
                data = remove_special_data(form.data.items())
                q = "UPDATE batch SET {} WHERE id = ${:d}".format(
                    settings(data), len(data) + 1
                )
                try:
                    await conn.execute(q, *data.values(), id_)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot edit the batch"))
                else:
                    flash(request, ("success", "batch successfuly edited"))
                    return HTTPFound(request.app.router["list_batch"].url_for())
            else:
                flash(request, ("danger", "there are some fields in error"))
            return {"id": id_, "form": form}
        elif request.method == "GET":
            form = BatchForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": id_, "form": form}
        else:
            raise HTTPMethodNotAllowed()


@require("admin")
@aiohttp_jinja2.template("list-batch.html")
async def list_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, date, capacity, opened FROM batch ORDER BY date DESC LIMIT 30"
        )
    return {"batches": rows}
