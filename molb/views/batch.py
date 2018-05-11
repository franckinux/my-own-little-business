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

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import field_list
from molb.views.utils import generate_csrf_meta
from molb.views.utils import place_holders
from molb.views.utils import remove_special_data
from molb.views.utils import RollbackTransactionException
from molb.views.utils import settings


class BatchForm(CsrfForm):
    date = DateTimeField("Date", validators=[Required()])
    opened = BooleanField("Ouverte", default=True)
    submit = SubmitField("Valider")


@require("admin")
@aiohttp_jinja2.template("create-batch.html")
async def create_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        # select all available products
        rows = await conn.fetch(
            "SELECT id, name, description, price FROM product WHERE available"
        )
        products = [dict(p) for p in rows]

        if request.method == "POST":
            form = BatchForm(await request.post(), meta=await generate_csrf_meta(request))
            data = remove_special_data(await request.post())

            for product in products:
                product_id = product["id"]
                quantity = data["product_qty_{}".format(product_id)]
                product["quantity"] = quantity

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", "Le formulaire comporte des erreurs."))
                return {"form": form, "products": products}

            # 2 separate loops for correct form rendering
            quantities = {}
            for product in products:
                product_id = product["id"]
                qti = product["quantity"].strip()
                if qti == '':
                    qti = 0
                else:
                    try:
                        qti = int(qti)
                        if qti < 0:
                            raise ValueError("negative quantity")
                    except ValueError:
                        flash(request, ("danger", "Quantité(s) invalide(s)."))
                        return {"form": form, "products": products}
                quantities[product_id] = qti

            if sum(quantities.values()) == 0:
                flash(request, ("warning", "Veuillez choisir au moins un produit"))
                return {"form": form, "products": products}

            try:
                async with conn.transaction():
                    # create the batch
                    q = (
                        "INSERT INTO batch (date, opened) "
                        "VALUES ($1, $2) RETURNING id"
                    )
                    batch_id = await conn.fetchval(q, form.data["date"], form.data["opened"])

                    # create batch to products
                    for product_id, quantity in quantities.items():
                        if quantity != 0:
                            q = (
                                "INSERT INTO batch_product_association ("
                                "   quantity, batch_id, product_id"
                                ") "
                                "VALUES ($1, $2, $3)"
                            )
                            await conn.execute(q, quantity, batch_id, product_id)

                flash(request, ("success", "Fournée a bien été crée"))
            except RollbackTransactionException:
                flash(request, ("warning", "La fournée ne peut pas être crée"))
                return {"form": form, "products": products}
            return HTTPFound(request.app.router["list_batch"].url_for())
        elif request.method == "GET":
            form = BatchForm(meta=await generate_csrf_meta(request))
            return {"form": form, "products": products}
        else:
            raise HTTPMethodNotAllowed()


@require("admin")
async def delete_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        try:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM batch_product_association WHERE batch_id = $1",
                    id_
                )
                await conn.execute("DELETE FROM batch WHERE id = $1", id_)
        except IntegrityConstraintViolationError:
            flash(request, ("warning", "La fournée ne peux pas être supprimée"))
        except Exception:
            flash(request, ("danger", "La fournée ne peux pas être supprimée"))
        else:
            flash(request, ("success", "La fournée a bien été supprimée"))
        finally:
            return HTTPFound(request.app.router["list_batch"].url_for())


@require("admin")
@aiohttp_jinja2.template("edit-batch.html")
async def edit_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        id_ = int(request.match_info["id"])
        data = dict(await conn.fetchrow("SELECT * FROM batch WHERE id = $1", id_))

        # select batch products
        q = (
            "SELECT name, description, price, available, quantity "
            "FROM product AS p "
            "INNER JOIN batch_product_association AS bpa ON bpa.product_id = p.id "
            "WHERE bpa.batch_id = $1"
        )
        rows = await conn.fetch(q, id_)
        products = [dict(p) for p in rows]

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
                    flash(request, ("warning", "La fournée ne peut pas être modifiée"))
                else:
                    flash(request, ("success", "La fournée a bien été modifiée"))
                    return HTTPFound(request.app.router["list_batch"].url_for())
            else:
                flash(request, ("danger", "Le formulaire contient des erreurs"))
            return {"id": str(id_), "form": form, "products": products}
        elif request.method == "GET":
            form = BatchForm(data=data, meta=await generate_csrf_meta(request))
            return {"id": str(id_), "form": form, "products": products}
        else:
            raise HTTPMethodNotAllowed()


@require("admin")
@aiohttp_jinja2.template("list-batch.html")
async def list_batch(request):
    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT CAST(id AS TEXT), date, opened "
            "FROM batch "
            "WHERE date > NOW() "
            "ORDER BY date DESC "
            "LIMIT 30"
        )
        rows = await conn.fetch(q)
    return {"batches": rows}
