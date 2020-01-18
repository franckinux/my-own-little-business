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
from wtforms.validators import Required

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import _l
from molb.views.utils import field_list
from molb.views.utils import flash
from molb.views.utils import generate_csrf_meta
from molb.views.utils import place_holders
from molb.views.utils import remove_special_data
from molb.views.utils import settings


class ProductForm(CsrfForm):
    name = StringField(
        _l("Nom"),
        validators=[
            Required(),
            Length(min=6, max=128)],
        render_kw={"placeholder": _l("Entrez le nom")}
    )
    name_lang1 = StringField(
        _l("Nom"),
        validators=[
            Required(),
            Length(min=6, max=128)
        ],
        render_kw={"placeholder": _l("Entrez le nom")}
    )
    description = StringField(
        _l("Description"),
        render_kw={"placeholder": _l("Entrez la description")}
    )
    description_lang1 = StringField(
        _l("Description"),
        render_kw={"placeholder": _l("Entrez la description")}
    )
    price = DecimalField(
        _l("Prix"),
        validators=[Required()],
        render_kw={"placeholder": _l("Entrez le prix")}
    )
    load = DecimalField(
        _l("Poids du pâton"),
        validators=[Required()],
        render_kw={"placeholder": _l("Entrez le poids du pâton")}
    )
    available = BooleanField(_l("Disponible"), default=True)
    submit = SubmitField(_l("Valider"))


@require("admin")
@aiohttp_jinja2.template("create-product.html")
async def create_product(request):
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
                    flash(request, ("warning", _("Le produit ne peut pas être créé")))
                    return {"form": form}
            flash(request, ("success", _("Le produit a été créé")))
            return HTTPFound(request.app.router["list_product"].url_for())
        else:
            flash(request, ("danger", _("Le formulaire contient des erreurs.")))
            return {"form": form}
    elif request.method == "GET":
        form = ProductForm(meta=await generate_csrf_meta(request))
        return {"form": form}
    else:
        raise HTTPMethodNotAllowed()


@require("admin")
async def delete_product(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        try:
            await conn.execute("DELETE FROM product WHERE id = $1", id_)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", _("Le produit ne peut pas être supprimé")))
        else:
            flash(request, ("success", _("Le produit a été supprimé")))
        finally:
            return HTTPFound(request.app.router["list_product"].url_for())


@require("admin")
@aiohttp_jinja2.template("edit-product.html")
async def edit_product(request):
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
                    flash(request, ("warning", _("Le produit ne peut pas être modifié")))
                else:
                    flash(request, ("success", _("Le produit a été modifié")))
                    return HTTPFound(request.app.router["list_product"].url_for())
            else:
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
            return {"id": str(id_), "form": form}
        elif request.method == "GET":
            form = ProductForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": str(id_), "form": form}
        else:
            raise HTTPMethodNotAllowed()


@require("admin")
@aiohttp_jinja2.template("list-product.html")
async def list_product(request):
    async with request.app["db-pool"].acquire() as conn:
        rows = await conn.fetch("SELECT CAST(id AS TEXT), name, available, price , load FROM product ORDER BY name")
    return {"products": rows}
