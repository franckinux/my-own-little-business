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
    name = StringField("Name", [validators.Required(), validators.Length(min=6, max=128)])
    opened = BooleanField("Opened")


@aiohttp_jinja2.template("create-repository.html")
async def create_repository(request):
    if request.method not in ["GET", "POST"]:
        raise HTTPMethodNotAllowed()

    async with request.app["engine"].acquire() as conn:
        if request.method == "POST":
            form = RepositoryForm(await request.post())
            if form.validate():
                q = insert(Repository).values(**dict(form.data.items()))
                try:
                    await conn.execute(q)
                except IntegrityError as e:
                    message = "cannot create the repository"
                    return {"form": form, "warning_message": message}
                message = "repository successfuly created"
                return {"form": form, "success_message": message}
            else:
                message = "there are some fields in error"
                return {"form": form, "warning_message": message}
        else:  # GET !
            form = RepositoryForm()
            return {"form": form}


@aiohttp_jinja2.template("list-repository.html")
async def delete_repository(request):
    async with request.app["engine"].acquire() as conn:
        id_ = int(request.match_info["id"])
        q = delete(Repository).where(Repository.__table__.c.id == id_)
        ok = False
        try:
            result = await conn.execute(q)
            message = "successfuly deleted"
            ok = True
        except IntegrityError:
            message = "cannot delete repository"
        finally:
            result = await conn.execute(select([Repository]).order_by(Repository.__table__.c.name))
            rows = await result.fetchall()
            if ok:
                return {"repositories": rows, "success_message": message}
            else:
                return {"repositories": rows, "warning_message": message}


@aiohttp_jinja2.template("edit-repository.html")
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
                q = update(Repository).where(
                    Repository.__table__.c.id == id_).values(**dict(form.data.items())
                    )
                try:
                    await conn.execute(q)
                except IntegrityError:
                    message = "cannot edit the repository"
                    return {"id": id_, "form": form, "warning_message": message}
                message = "repository successfuly edited"
                return {"id": id_, "form": form, "success_message": message}
            else:
                message = "there are some fields in error"
                return {"id": id_, "form": form, "warning_message": message}
        else:  # GET !
            form = RepositoryForm(data=data)
            return {"id": id_, "form": form}


@aiohttp_jinja2.template("list-repository.html")
async def list_repository(request):
    async with request.app["engine"].acquire() as conn:
        result = await conn.execute(select([Repository]).order_by(Repository.__table__.c.name))
        rows = await result.fetchall()
    return {"repositories": rows}
