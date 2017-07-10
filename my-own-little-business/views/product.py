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
from wtforms import DecimalField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import validators

from .csrf_form import CsrfForm
from .flash_messages import *
from model import Product
from utils import generate_csrf_meta
from utils import remove_special_data


class ProductForm(CsrfForm):
    name = StringField("Name", [validators.Required(), validators.Length(min=6, max=128)])
    description = StringField("Description")
    price = DecimalField("Price", [validators.Required()])
    load = DecimalField("Load", [validators.Required()])
    available = BooleanField("Available")
    submit = SubmitField("Submit")


@aiohttp_jinja2.template("create-product.html")
async def create_product(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        if request.method == "POST":
            form = ProductForm(await request.post(), meta=await generate_csrf_meta(request))
            if form.validate():
                q = insert(Product).values(**remove_special_data(form.data.items()))
                try:
                    await conn.execute(q)
                except IntegrityError:
                    flash(request, (WARNING, "cannot create the product"))
                    return {"form": form}
                flash(request, (SUCCESS, "product successfuly created"))
                return {"form": form}
            else:
                flash(request, (ERROR, "there are some fields in error"))
                return {"form": form}
        else:  # GET !
            form = ProductForm(meta=await generate_csrf_meta(request))
            return {"form": form}


@aiohttp_jinja2.template("list-product.html")
async def delete_product(request):
    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Product).where(Product.__table__.c.id == id_)
        try:
            result = await conn.execute(q)
        except IntegrityError:
            flash(request, (WARNING, "cannot delete the product"))
        else:
            flash(request, (SUCCESS, "product successfuly deleted"))
        finally:
            result = await conn.execute(select([Product]).order_by(Product.__table__.c.name))
            rows = await result.fetchall()
            return {"products": rows}


@aiohttp_jinja2.template("edit-product.html")
async def edit_product(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = select([Product], Product.__table__.c.id == id_)
        result = await conn.execute(q)
        data = dict(await result.fetchone())
        if request.method == "POST":
            form = ProductForm(
                await request.post(),
                data=data,
                meta=await generate_csrf_meta(request)
            )
            if form.validate():
                q = update(Product).where(
                    Product.__table__.c.id == id_).values(**remove_special_data(form.data.items())
                    )
                try:
                    await conn.execute(q)
                except IntegrityError:
                    flash(request, (WARNING, "cannot edit the product"))
                    return {"id": id_, "form": form}
                flash(request, (SUCCESS, "product successfuly edited"))
                return {"id": id_, "form": form}
            else:
                flash(request, (ERROR, "there are some fields in error"))
                return {"id": id_, "form": form}
        else:  # GET !
            form = ProductForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": id_, "form": form}


@aiohttp_jinja2.template("list-product.html")
async def list_product(request):
    async with request.app["engine"].acquire() as conn:
        result = await conn.execute(select([Product]).order_by(Product.__table__.c.name))
        rows = await result.fetchall()
    return {"products": rows}