from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
from aiohttp.web import Response
from aiohttp_babel.middlewares import _
import aiohttp_jinja2
from multidict import MultiDict
from wtforms import BooleanField
from wtforms import SelectField
from wtforms import SubmitField

from molb.auth import require
from molb.views.csrf_form import CsrfForm
from molb.views.utils import _l
from molb.views.utils import flash
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data


class PlanForm(CsrfForm):
    batch_id = SelectField(_l("Fournée"), coerce=int)
    export = BooleanField(_l("Exporter"))
    submit = SubmitField(_l("Valider"))


@require("admin")
@aiohttp_jinja2.template("plan.html")
async def plan(request):
    async with request.app["db-pool"].acquire() as conn:
        # select last 10 opened batches that have orders on them
        q = (
            "WITH sq AS ("
            "    SELECT DISTINCT b.id AS batch_id, b.date AS batch_date_ "
            "    FROM order_ AS o "
            "    INNER JOIN batch AS b ON o.batch_id = b.id "
            "    WHERE b.opened "
            "    ORDER BY b.date DESC "
            "    LIMIT 10"
            ") "
            "SELECT batch_id, TO_CHAR(batch_date_::DATE, 'dd-mm-yyyy') AS batch_date "
            "FROM sq"
        )
        rows = await conn.fetch(q)
        batch_choices = [(row["batch_id"], row["batch_date"]) for row in rows]

        if request.method == "POST":
            form = PlanForm(await request.post(), meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices

            data = remove_special_data(form.data)
            batch_id = int(data["batch_id"])

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
                return HTTPFound(request.app.router["plan"].url_for())

            if data["export"]:
                # get the number of products by repository by clients to make from the batch
                q = (
                    "SELECT r.name AS repository_name, c.last_name, c.first_name,"
                    "       p.name AS product_name, "
                    "       CAST(SUM(opa.quantity) AS TEXT) AS quantity "
                    "FROM order_product_association AS opa "
                    "INNER JOIN product AS p ON opa.product_id = p.id "
                    "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    "INNER JOIN batch AS b ON o.batch_id = b.id "
                    "INNER JOIN client AS c ON o.client_id = c.id "
                    "INNER JOIN repository AS r ON c.repository_id = r.id "
                    "WHERE b.id = $1 "
                    "GROUP BY r.id, c.id, p.id "
                    "ORDER BY r.name, c.last_name, c.first_name, p.name"
                )
                rows = await conn.fetch(q, batch_id)

                body = ""
                for r in rows:
                    body += ','.join(r) + '\n'

                return Response(
                    headers=MultiDict(
                        {
                            "Content-Disposition": "Attachment; filename=plan.csv",
                            "Content-Type": "text/csv"
                        }
                    ),
                    body=body
                )
            else:
                # get the number of products to make from the batch
                q = (
                    "SELECT p.name, SUM(opa.quantity) AS quantity "
                    "FROM order_product_association AS opa "
                    "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    "INNER JOIN product AS p ON opa.product_id = p.id "
                    "INNER JOIN batch AS b ON o.batch_id = b.id "
                    "WHERE b.id = $1 "
                    "GROUP BY p.id"
                )
                products = await conn.fetch(q, batch_id)

                # compute batch load
                q = (
                    "SELECT b.id, b.capacity, SUM(opa.quantity * p.load) AS load "
                    "FROM order_product_association AS opa "
                    "INNER JOIN product AS p ON opa.product_id = p.id "
                    "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    "INNER JOIN batch AS b ON o.batch_id = b.id "
                    "WHERE b.id = $1 "
                    "GROUP BY b.id"
                )
                batch = await conn.fetchrow(q, batch_id)

                # get the number of products by repository to make from the batch
                q = (
                    "SELECT r.name AS repository_name, p.name AS product_name, "
                    "       SUM(opa.quantity) AS quantity "
                    "FROM order_product_association AS opa "
                    "INNER JOIN product AS p ON opa.product_id = p.id "
                    "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    "INNER JOIN batch AS b ON o.batch_id = b.id "
                    "INNER JOIN client AS c ON o.client_id = c.id "
                    "INNER JOIN repository AS r ON c.repository_id = r.id "
                    "WHERE b.id = $1 "
                    "GROUP BY r.id, p.id "
                    "ORDER BY r.name, p.name"
                )
                products_by_repository = await conn.fetch(q, batch_id)

                # get the number of products by repository by clients to make from the batch
                q = (
                    "SELECT r.name AS repository_name, c.last_name, c.first_name,"
                    "       p.name AS product_name, SUM(opa.quantity) AS quantity "
                    "FROM order_product_association AS opa "
                    "INNER JOIN product AS p ON opa.product_id = p.id "
                    "INNER JOIN order_ AS o ON opa.order_id = o.id "
                    "INNER JOIN batch AS b ON o.batch_id = b.id "
                    "INNER JOIN client AS c ON o.client_id = c.id "
                    "INNER JOIN repository AS r ON c.repository_id = r.id "
                    "WHERE b.id = $1 "
                    "GROUP BY r.id, c.id, p.id "
                    "ORDER BY r.name, c.last_name, c.first_name, p.name"
                )
                products_by_repository_by_client = await conn.fetch(q, batch_id)

                return {
                    "form": form,
                    "batch": batch,
                    "products": products,
                    "products_by_repository": products_by_repository,
                    "products_by_repository_by_client": products_by_repository_by_client,
                }

        elif request.method == "GET":
            form = PlanForm(meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices
            return {"form": form}
        else:
            raise HTTPMethodNotAllowed()
