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
from wtforms import StringField
from wtforms import validators

from model import Repository


class RepositoryForm(Form):
    name = StringField("Name", [validators.Required(), validators.Length(min=4, max=128)])
    opened = BooleanField("Opened")


@aiohttp_jinja2.template("create_repository.html")
async def create_repository(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        if request.method == "POST":
            form = RepositoryForm(await request.post())
            if form.validate():
                q = insert(Repository).values(**dict(form.data.items()))
                await conn.execute(q)
                return HTTPFound("/repository/list/")
            else:
                return {"form": form}
        else:  # GET !
            form = RepositoryForm()
            return {"form": form}


async def delete_repository(request):
    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Repository).where(Repository.__table__.c.id == id_)
        try:
            result = await conn.execute(q)
        except IntegrityError:
            # display an error message
            pass
        return HTTPFound("/repository/list/")


@aiohttp_jinja2.template("edit_repository.html")
async def edit_repository(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = select([Repository], Repository.__table__.c.id == id_)
        result = await conn.execute(q)
        data = dict(await result.fetchone())
        if request.method == "POST":
            form = RepositoryForm(await request.post(), data=data)
            if form.validate():
                q = update(Repository).where(Repository.__table__.c.id == id_).values(**dict(form.data.items()))
                await conn.execute(q)
                return HTTPFound("/repository/edit/{}/".format(id_))
            else:
                return {"id": id_, "form": form}
        else:  # GET !
            form = RepositoryForm(data=data)
            return {"id": id_, "form": form}


@aiohttp_jinja2.template("list_repository.html")
async def list_repository(request):
    async with request.app["engine"].acquire() as conn:
        result = await conn.execute(select([Repository]).order_by(Repository.__table__.c.name))
        rows = await result.fetchall()
    return {"repositories": rows}
