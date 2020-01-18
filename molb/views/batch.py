from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_babel.middlewares import _
import aiohttp_jinja2
from asyncpg.exceptions import IntegrityConstraintViolationError
from datetime import datetime
from datetime import time
from wtforms import BooleanField
from wtforms import DateField
from wtforms import DecimalField
from wtforms import SubmitField
from wtforms.validators import Required
from wtforms.validators import ValidationError

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import _l
from molb.views.utils import flash
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data
from molb.views.utils import settings


class BatchForm(CsrfForm):
    date = DateField(_l("Date"), id="date", format="%d/%m/%Y", validators=[Required()])
    capacity = DecimalField(
        _l("Capacité"),
        validators=[Required()],
        render_kw={"placeholder": _l("Entrez la capacité de la fournée")}
    )
    opened = BooleanField(_l("Ouverte"), default=True)
    submit = SubmitField(_l("Valider"))

    def validate_capacity(form, field):
        if int(field.data) <= 0:
            raise ValidationError(_l("Valeur négative ou nulle"))


@require("admin")
@aiohttp_jinja2.template("create-batch.html")
async def create_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        if request.method == "POST":
            form = BatchForm(await request.post(), meta=await generate_csrf_meta(request))
            data = remove_special_data(form.data.items())

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
                return {"form": form}

            # as the date only is chosen by the user, the time part is set to 6:00 am
            data["date"] = datetime.combine(data["date"], time(hour=6))

            try:
                async with conn.transaction():
                    # create the batch
                    q = (
                        "INSERT INTO batch (date, capacity, opened) VALUES ($1, $2, $3)"
                    )
                    await conn.execute(
                        q, data["date"], data["capacity"], data["opened"]
                    )

                flash(request, ("success", _("La fournée a été créée")))
            except Exception:
                flash(request, ("warning", _("La fournée ne peut pas être créée")))
                return {"form": form}
            return HTTPFound(request.app.router["list_batch"].url_for())
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
            async with conn.transaction():
                await conn.execute("DELETE FROM batch WHERE id = $1", id_)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", _("La fournée ne peut pas être supprimée")))
        except Exception:
            flash(request, ("danger", _("La fournée ne peut pas être supprimée")))
        else:
            flash(request, ("success", _("La fournée a été supprimée")))
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
                # as the date only is chosen by the user, the time part is set to 6:00 am
                data["date"] = datetime.combine(data["date"], time(hour=6))

                q = "UPDATE batch SET {} WHERE id = ${:d}".format(
                    settings(data), len(data) + 1
                )
                try:
                    await conn.execute(q, *data.values(), id_)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", _("La fournée ne peut pas être modifiée")))
                else:
                    flash(request, ("success", _("La fournée a été modifiée")))
                    return HTTPFound(request.app.router["list_batch"].url_for())
            else:
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
            return {"id": str(id_), "form": form}
        elif request.method == "GET":
            form = BatchForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": str(id_), "form": form}
        else:
            raise HTTPMethodNotAllowed()


@require("admin")
@aiohttp_jinja2.template("list-batch.html")
async def list_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT CAST(id AS TEXT), date, capacity, opened "
            "FROM batch "
            "WHERE date > NOW() "
            "ORDER BY date ASC "
            "LIMIT 30"
        )
        rows = await conn.fetch(q)
    return {"batches": rows}
