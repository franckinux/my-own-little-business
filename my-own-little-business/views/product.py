from aiohttp.web import HTTPMethodNotAllowed
from aiohttp.web import HTTPFound
import aiohttp_jinja2
from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.sql import delete
from sqlalchemy.sql import insert
from sqlalchemy.sql import update
from wtforms import Form
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import StringField
from wtforms import validators

from model import Product


class ProductForm(Form):
    name = StringField("Name", [validators.Required(), validators.Length(min=6, max=128)])
    description = StringField("Description")
    price = DecimalField("Price", [validators.Required()])
    load = DecimalField("Load", [validators.Required()])
    available = BooleanField("Available")


@aiohttp_jinja2.template("create-product.html")
async def create_product(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        if request.method == "POST":
            form = ProductForm(await request.post())
            if form.validate():
                q = insert(Product).values(**dict(form.data.items()))
                try:
                    await conn.execute(q)
                except IntegrityError as e:
                    message = "cannot create the product"
                    return {"form": form, "warning_message": message}
                message = "product successfuly created"
                return {"form": form, "success_message": message}
            else:
                message = "there are some fields in error"
                return {"form": form, "warning_message": message}
        else:  # GET !
            form = ProductForm()
            return {"form": form}


@aiohttp_jinja2.template("list-product.html")
async def delete_product(request):
    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Product).where(Product.__table__.c.id == id_)
        ok = False
        try:
            result = await conn.execute(q)
            message = "successfuly deleted"
            ok = True
        except IntegrityError:
            message = "cannot delete product"
        finally:
            result = await conn.execute(select([Product]).order_by(Product.__table__.c.name))
            rows = await result.fetchall()
            if ok:
                return {"products": rows, "success_message": message}
            else:
                return {"products": rows, "warning_message": message}


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
            form = ProductForm(await request.post(), data=data)
            if form.validate():
                q = update(Product).where(
                    Product.__table__.c.id == id_).values(**dict(form.data.items())
                    )
                try:
                    await conn.execute(q)
                except IntegrityError:
                    message = "cannot edit the product"
                    return {"id": id_, "form": form, "warning_message": message}
                message = "product successfuly edited"
                return {"id": id_, "form": form, "success_message": message}
            else:
                message = "there are some fields in error"
                return {"id": id_, "form": form, "warning_message": message}
        else:  # GET !
            form = ProductForm(data=data)
            return {"id": id_, "form": form}


@aiohttp_jinja2.template("list-product.html")
async def list_product(request):
    async with request.app["engine"].acquire() as conn:
        result = await conn.execute(select([Product]).order_by(Product.__table__.c.name))
        rows = await result.fetchall()
    return {"products": rows}
