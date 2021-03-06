from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp_babel.middlewares import _
import aiohttp_jinja2
from asyncpg.exceptions import IntegrityConstraintViolationError
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import Length
from wtforms.validators import DataRequired
from wtforms.validators import ValidationError

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import _l
from molb.views.utils import array_to_days
from molb.views.utils import days_to_array
from molb.views.utils import flash
from molb.views.utils import field_list
from molb.views.utils import generate_csrf_meta
from molb.views.utils import place_holders
from molb.views.utils import remove_special_data
from molb.views.utils import settings


class RepositoryForm(CsrfForm):
    name = StringField(
        _l("Dénomination"),
        validators=[DataRequired(), Length(min=5, max=128)],
        render_kw={"placeholder": _l("Entrez le nom")}
    )
    latitude = DecimalField(
        _l("Latitude"),
        places=6,
        validators=[DataRequired()],
        render_kw={"placeholder": _l("Entrez la latitude")}
    )
    longitude = DecimalField(
        _l("Longitude"),
        places=6,
        validators=[DataRequired()],
        render_kw={"placeholder": _l("Entrez la longitude")}
    )

    def validate_latitude(form, field):
        if not -90 <= float(field.data) <= 90:
            raise ValidationError(_l("Valeur incorrecte"))

    def validate_longitude(form, field):
        if not -180 <= float(field.data) <= 180:
            raise ValidationError(_l("Valeur incorrecte"))
    opened = BooleanField(_l("Ouvert"), default=True)
    monday = BooleanField(_l("Lundi"))
    tuesday = BooleanField(_l("Mardi"))
    wednesday = BooleanField(_l("Mercredi"))
    thursday = BooleanField(_l("Jeudi"))
    friday = BooleanField(_l("Vendredi"))
    saturday = BooleanField(_l("Samedi"))
    sunday = BooleanField(_l("Dimanche"))
    submit = SubmitField(_l("Valider"))


@require("admin")
@aiohttp_jinja2.template("create-repository.html")
async def create_repository(request):
    if request.method == "POST":
        form = RepositoryForm(await request.post(), meta=await generate_csrf_meta(request))
        if form.validate():
            data = remove_special_data(form.data)
            data = days_to_array(data)
            async with request.app["db-pool"].acquire() as conn:
                q = "INSERT INTO repository ({}) VALUES ({})".format(
                    field_list(data), place_holders(data)
                )
                try:
                    await conn.execute(q, *data.values())
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", _("Le point de livraison ne peut pas être créé")))
                    return {"form": form}
            flash(request, ("success", _("Le point de livraison a été créé")))
            return HTTPFound(request.app.router["list_repository"].url_for())
        else:
            flash(request, ("danger", _("Le formulaire contient des erreurs.")))
            return {"form": form}
    elif request.method == "GET":
        form = RepositoryForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


@require("admin")
async def delete_repository(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        try:
            await conn.execute("DELETE FROM repository WHERE id = $1", id_)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", _("Le point de livraison ne peut pas être supprimé")))
        else:
            flash(request, ("success", _("Le point de livraison a été supprimé")))
        finally:
            return HTTPFound(request.app.router["list_repository"].url_for())


@require("admin")
@aiohttp_jinja2.template("edit-repository.html")
async def edit_repository(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        data = dict(await conn.fetchrow("SELECT * FROM repository WHERE id = $1", id_))
        data = array_to_days(data)
        if request.method == "POST":
            form = RepositoryForm(
                await request.post(),
                data=data,
                meta=await generate_csrf_meta(request)
            )
            if form.validate():
                data = remove_special_data(form.data)
                data = days_to_array(data)
                q = "UPDATE repository SET {} WHERE id = ${:d}".format(
                    settings(data), len(data) + 1
                )
                try:
                    await conn.execute(q, *data.values(), id_)
                except IntegrityConstraintViolationError:
                    flash(request, ("warning", _("Le point de livraison ne peut pas être modifié")))
                else:
                    flash(request, ("success", _("Le point de livraison a été modifié")))
                    return HTTPFound(request.app.router["list_repository"].url_for())
            else:
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
            return {"id": str(id_), "form": form}
        elif request.method == "GET":
            form = RepositoryForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": str(id_), "form": form}
        else:
            raise HTTPMethodNotAllowed()


@require("admin")
@aiohttp_jinja2.template("list-repository.html")
async def list_repository(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch("SELECT CAST(id AS TEXT), name, opened FROM repository ORDER BY name")
    return {"repositories": rows}
