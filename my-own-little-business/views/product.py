from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from asyncpg.exceptions import IntegrityConstraintViolationError
from sqlalchemy import select
from sqlalchemy.sql import delete
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Length
from wtforms.validators import Required

from auth import require
from .csrf_form import CsrfForm
from model import Product
from views.utils import generate_csrf_meta
from views.utils import remove_special_data


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
            async with request.app["db-pool"].acquire() as conn:
                q = insert(Product).values(**remove_special_data(form.data.items()))
                try:
                    await conn.fetchrow(q)
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
@aiohttp_jinja2.template("list-product.html")
async def delete_product(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Product).where(Product.__table__.c.id == id_)
        try:
            await conn.fetchrow(q)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", "cannot delete the product"))
        else:
            flash(request, ("success", "product successfuly deleted"))
        finally:
            rows = await conn.fetch(select([Product]).order_by(Product.__table__.c.name))
            return {"products": rows}


@require("admin")
@aiohttp_jinja2.template("edit-product.html")
async def edit_product(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    id_ = int(request.match_info["id"])
    q = select([Product], Product.__table__.c.id == id_)
    data = dict(await conn.fetchrow(q))
    if request.method == "POST":
        form = ProductForm(
            await request.post(),
            data=data,
            meta=await generate_csrf_meta(request)
        )
        if form.validate():
            async with request.app["db-pool"].acquire() as conn:
                q = update(Product).where(
                    Product.__table__.c.id == id_).values(**remove_special_data(form.data.items())
                )
                try:
                    await conn.fetchrow(q)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", "cannot edit the product"))
                else:
                    flash(request, ("success", "product successfuly edited"))
            return {"id": id_, "form": form}
        else:
            flash(request, ("danger", "there are some fields in error"))
            return {"id": id_, "form": form}
    else:  # GET !
        form = ProductForm(data=data, meta=await generate_csrf_meta(request))
        return {"id": id_, "form": form}


@require("admin")
@aiohttp_jinja2.template("list-product.html")
async def list_product(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch(select([Product]).order_by(Product.__table__.c.name))
    return {"products": rows}
