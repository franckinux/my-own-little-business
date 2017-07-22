from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import IntegrityConstraintViolationError
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Length
from wtforms.validators import Required

from auth import require
from .csrf_form import CsrfForm
from views.utils import field_list
from views.utils import generate_csrf_meta
from views.utils import place_holders
from views.utils import remove_special_data
from views.utils import settings


class ProductForm(CsrfForm):
    name = StringField("Name", validators=[Required(), Length(min=6, max=128)])
    description = StringField("Description")
    price = DecimalField("Price", validators=[Required()])
    load = DecimalField("Load", validators=[Required()])
    available = BooleanField("Available")
    submit = SubmitField("Submit")


@require("admin")
@aiohttp_jinja2.template("create-product.html")
async def create_product(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    if request.method == "POST":
        form = ProductForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            data = remove_special_data(form.data.items())
            async with request.app["db-pool"].acquire() as conn:
                q = "INSERT INTO product ({}) VALUES ({})".format(
                    field_list(data), place_holders(data)
                )
                try:
                    await conn.execute(q, *data.values())
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot create the product"))
                    return {"form": form}
            flash(request, ("success", "product successfuly created"))
            return {"form": form}
        else:
            flash(request, ("danger", "there are some fields in error"))
            return {"form": form}
    else:  # GET !
        form = ProductForm(meta=await generate_csrf_meta(request))
        return {"form": form}


@require("admin")
async def delete_product(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        try:
            await conn.execute("DELETE FROM product WHERE id = $1", id_)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", "cannot delete the product"))
        else:
            flash(request, ("success", "product successfuly deleted"))
        finally:
            return HTTPFound(request.app.router["list_product"].url_for())


@require("admin")
@aiohttp_jinja2.template("edit-product.html")
async def edit_product(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        data = dict(await conn.fetchrow("SELECT * FROM product WHERE id = $1", id_))
        if request.method == "POST":
            form = ProductForm(
                await request.post(),
                data=data,
                meta=await generate_csrf_meta(request)
            )
            if form.validate():
                data = remove_special_data(form.data.items())
                q = "UPDATE product SET {} WHERE id = ${:d}".format(
                    settings(data), len(data) + 1
                )
                try:
                    await conn.execute(q, *data.values(), id_)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot edit the product"))
                else:
                    flash(request, ("success", "product successfuly edited"))
            else:
                flash(request, ("danger", "there are some fields in error"))
        else:  # GET !
            form = ProductForm(data=data, meta=await generate_csrf_meta(request))
        return {"id": id_, "form": form}


@require("admin")
@aiohttp_jinja2.template("list-product.html")
async def list_product(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch("SELECT id, name, available FROM product ORDER by name")
    return {"products": rows}
