from datetime import datetime
from datetime import timedelta

from aiohttp_security import authorized_userid
from aiohttp.web import HTTPFound
from aiohttp.web import HTTPMethodNotAllowed
import aiohttp_jinja2
from aiohttp_session_flash import flash
from wtforms import SelectField
from wtforms import SubmitField

from molb.auth import require
from molb.main import _
from molb.views.csrf_form import CsrfForm
from molb.views.utils import generate_csrf_meta
from molb.views.utils import remove_special_data


class CreateOrderForm(CsrfForm):
    batch_id = SelectField(_("Fournée"), coerce=int)
    submit = SubmitField(_("Valider"))


class FillOrderForm(CsrfForm):
    submit = SubmitField(_("Valider"))


async def get_ordered_products_load(conn, batch_id, excluded=None):
    """Return the load of already ordered products"""

    # get summed quantities of all orders
    if excluded is not None:
        q = (
            "SELECT SUM(quantity*p.load) AS load "
            "FROM order_product_association "
            "INNER JOIN order_ AS o ON o.id = order_id "
            "INNER JOIN product AS p ON p.id = product_id "
            "WHERE p.available AND o.batch_id = $1 AND order_id != $2"
        )
        load = await conn.fetchval(q, batch_id, excluded)
    else:
        q = (
            "SELECT SUM(quantity*p.load) AS load "
            "FROM order_product_association "
            "INNER JOIN order_ AS o ON o.id = order_id "
            "INNER JOIN product AS p ON p.id = product_id "
            "WHERE p.available AND o.batch_id = $1"
        )
        load = await conn.fetchval(q, batch_id)
    if load is None:
        load = 0
    return load


@require("client")
@aiohttp_jinja2.template("create-order.html")
async def create_order(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT c.id, c.disabled, r.days "
            "FROM client AS c "
            "INNER JOIN repository AS r ON c.repository_id = r.id "
            "WHERE c.login = $1 "
        )
        client = await conn.fetchrow(q, login)
        client_id = client["id"]

        if client["disabled"]:
            flash(request, ("warning", _("Vous ne pouvez pas passer de commande.")))
            return HTTPFound(request.app.router["list_order"].url_for())

        # select opened batches that have no order from the client
        # select opened batches that have no order on them
        # from all above selected batches, select batches :
        #    - whose date is 12 hours in the future
        #    - client's delivery days corresponds to the batch date
        q = (
            "WITH batch_choices AS ( "
            "    SELECT b.id AS batch_id, b.date AS batch_date, c.id AS client_id FROM batch AS b "
            "    LEFT JOIN order_ AS o ON b.id = o.batch_id "
            "    LEFT JOIN client AS c ON c.id = o.client_id "
            "    WHERE b.opened AND b.date > (NOW() + INTERVAL '12 hour') AND "
            "          (string_to_array($2, ',')::boolean[])[EXTRACT(DOW FROM b.date) + 1] "
            "    GROUP BY b.id, b.date, c.id "
            "    ORDER BY b.id, b.date "
            ") "
            "SELECT batch_id, batch_date FROM batch_choices "
            "WHERE batch_id NOT IN ("
            "    SELECT batch_id FROM batch_choices "
            "    WHERE client_id = $1 "
            ")"
        )
        rows = await conn.fetch(q, client_id, str(client["days"]).strip("[]"))
        batch_choices = [(row["batch_id"], row["batch_date"]) for row in rows]

        # get all available products
        q = (
            "SELECT * FROM product WHERE available"
        )
        rows = await conn.fetch(q)
        products = {p["id"]: dict(p) for p in rows}

        template_context = {
            "products": products.values()
        }

        if request.method == "POST":
            data = await request.post()
            form = CreateOrderForm(data, meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices

            data = remove_special_data(data.items())
            batch_id = int(data["batch_id"])

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
                return HTTPFound(request.app.router["list_order"].url_for())

            # get the batch date and capacity
            q = "SELECT date, capacity FROM batch WHERE id = $1"
            row = await conn.fetchrow(q, batch_id)
            batch_date = row["date"]
            batch_capacity = row["capacity"]

            # check that the batch corresponds to the delivery days
            if not client["days"][(batch_date.weekday() + 1) % 7]:
                flash(request, ("warning", _("La fournée choisie ne permet de vous livrer.")))
                return HTTPFound(request.app.router["list_order"].url_for())

            template_context["form"] = form

            # compute total price and total_load of the order
            total_price = 0
            total_load = 0
            for product_id, product in products.items():
                ordered = data["product_qty_{}".format(product_id)].strip()
                if ordered == '':
                    ordered = 0
                else:
                    try:
                        ordered = int(ordered)
                        if ordered < 0:
                            raise ValueError("negative quantity")
                    except ValueError:
                        flash(request, ("danger", _("Quantité(s) invalide(s).")))
                        return template_context
                product["ordered"] = ordered
                total_price += ordered * products[product_id]["price"]
                total_load += ordered * products[product_id]["load"]

            # check that at least one product has been ordered
            if total_load == 0:
                flash(request, ("warning", _("Veuillez choisir au moins un produit")))
                return template_context

            # checked that the load of ordered products is less than the batch capacity
            products_load = await get_ordered_products_load(conn, batch_id)
            if total_load + products_load > batch_capacity:
                flash(
                    request,
                    (
                        "warning",
                        _("Votre commande dépasse la capacité de la fournée.")
                    )
                )
                return template_context

            try:
                async with conn.transaction():
                    # create the order
                    q = (
                        "INSERT INTO order_ (total, client_id, batch_id) "
                        "VALUES ($1, $2, $3) RETURNING id"
                    )
                    order_id = await conn.fetchval(q, total_price, client_id, batch_id)

                    # create order to products
                    for product_id, product in products.items():
                        ordered = product["ordered"]
                        if ordered != 0:
                            q = (
                                "INSERT INTO order_product_association ("
                                "   quantity, order_id, product_id"
                                ") "
                                "VALUES ($1, $2, $3)"
                            )
                            await conn.execute(q, ordered, order_id, product_id)
            except Exception:
                flash(request, ("warning", (_("Votre commande n'a pas pu être passée."))))
                return template_context

            flash(request, ("success", _("Votre commande a été passée avec succès")))
            return HTTPFound(request.app.router["list_order"].url_for())

        elif request.method == "GET":
            form = CreateOrderForm(meta=await generate_csrf_meta(request))
            form.batch_id.choices = batch_choices
            template_context["form"] = form
            return template_context

        else:
            raise HTTPMethodNotAllowed()


@require("client")
@aiohttp_jinja2.template("edit-order.html")
async def edit_order(request):
    order_id = int(request.match_info["id"])
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        q = (
            "SELECT c.id, c.disabled, r.days "
            "FROM client AS c "
            "INNER JOIN repository AS r ON c.repository_id = r.id "
            "WHERE c.login = $1 "
        )
        client = await conn.fetchrow(q, login)
        client_id = client["id"]

        if client["disabled"]:
            flash(request, ("warning", _("Vous ne pouvez pas modifier votre commande.")))
            return HTTPFound(request.app.router["list_order"].url_for())

        # check that the order belongs to the right client
        q = (
            "SELECT COUNT(*) FROM order_ "
            "WHERE id = $1 AND client_id = $2"
        )
        count = await conn.fetchval(q, order_id, client_id)
        if count != 1:
            return HTTPFound(request.app.router["list_order"].url_for())

        # get batch id and batch date
        q = (
            "SELECT batch_id, b.date, b.capacity FROM order_ AS o "
            "INNER JOIN batch AS b ON b.id = batch_id "
            "WHERE o.id = $1"
        )
        row = await conn.fetchrow(q, order_id)
        batch_date = row["date"]
        batch_id = row["batch_id"]
        batch_capacity = row["capacity"]

        # check that's its not too late to modify the order
        if datetime.now() > batch_date - timedelta(hours=12):
            flash(request, ("warning", _("Il est trop tard pour modifier votre commande.")))
            return HTTPFound(request.app.router["list_order"].url_for())

        # get products
        q = (
            "SELECT * FROM product WHERE available"
        )
        rows = await conn.fetch(q)
        products = {p["id"]: dict(p) for p in rows}

        template_context = {
            "batch_date": batch_date,
            "batch_id": batch_id,
            "order_id": order_id,
            "products": products.values()
        }

        if request.method == "POST":
            data = await request.post()
            form = FillOrderForm(await request.post(), meta=await generate_csrf_meta(request))
            data = remove_special_data(data)

            template_context["form"] = form

            # just for csrf !
            if not form.validate():
                flash(request, ("danger", _("Le formulaire contient des erreurs.")))
                return template_context

            # compute total price and total_load of the order
            total_price = 0
            total_load = 0
            for product_id, product in products.items():
                ordered = data["product_qty_{}".format(product_id)].strip()
                if ordered == '':
                    ordered = 0
                else:
                    try:
                        ordered = int(ordered)
                        if ordered < 0:
                            raise ValueError("negative quantity")
                    except ValueError:
                        flash(request, ("danger", _("Quantité(s) invalide(s).")))
                        return template_context
                product["ordered"] = ordered
                total_price += ordered * products[product_id]["price"]
                total_load += ordered * products[product_id]["load"]

            # check that at least one product has been ordered
            if total_load == 0:
                flash(request, ("warning", _("Veuillez choisir au moins un produit")))
                return template_context

            # checked that the load of ordered products is less than batch capacity
            products_load = await get_ordered_products_load(conn, batch_id, excluded=order_id)
            if total_load + products_load > batch_capacity:
                flash(
                    request,
                    (
                        "warning",
                        _("Votre commande dépasse la capacité de la fournée.")
                    )
                )
                return template_context

            # delete and re-create the order in a transaction
            try:
                async with conn.transaction():
                    # delete order to products association records
                    q = "DELETE FROM order_product_association WHERE order_id = $1"
                    await conn.execute(q, order_id)

                    # and re-create them
                    # create order to products
                    for product_id, product in products.items():
                        ordered = product["ordered"]
                        if ordered != 0:
                            q = (
                                "INSERT INTO order_product_association ("
                                "   quantity, order_id, product_id"
                                ") "
                                "VALUES ($1, $2, $3)"
                            )
                            await conn.execute(q, ordered, order_id, product_id)

                    # update order total
                    q = (
                        "UPDATE order_ SET total = $1, date=NOW() "
                        "WHERE id = $2"
                    )
                    await conn.fetchval(q, total_price, order_id)

            except Exception:
                flash(request, ("warning", (_("Votre commande n'a pas pu être modifiée."))))
                return template_context

            flash(request, ("success", _("Votre commande a été modifiée.")))
            return HTTPFound(request.app.router["list_order"].url_for())

        elif request.method == "GET":
            # select all the products from the order
            q = (
                "SELECT p.id, quantity "
                "FROM order_product_association AS opa "
                "INNER JOIN product AS p ON opa.product_id = p.id "
                "WHERE p.available AND opa.order_id = $1"
            )
            rows = await conn.fetch(q, order_id)

            # update the batch products with the order products
            for row in rows:
                products[row["id"]]["ordered"] = row["quantity"]

            form = FillOrderForm(meta=await generate_csrf_meta(request))
            template_context["form"] = form
            return template_context

        else:
            raise HTTPMethodNotAllowed()


@require("client")
async def delete_order(request):
    order_id = int(request.match_info["id"])
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client_id = await conn.fetchval(
            "SELECT id FROM client WHERE login = $1", login
        )

        # get and batch date
        batch_date = await conn.fetchval(
            "SELECT b.date FROM order_ AS o "
            "INNER JOIN batch AS b ON o.batch_id = b.id "
            "WHERE o.id = $1", order_id
        )
        if datetime.now() > batch_date - timedelta(hours=12):
            flash(request, ("warning", _("Il est trop tard pour annuler votre commande.")))
            return HTTPFound(request.app.router["list_order"].url_for())

        try:
            async with conn.transaction():
                # needs to be deleted before the order
                q = "DELETE FROM order_product_association WHERE order_id = $1"
                await conn.execute(q, order_id)

                # delete and check that the order belongs to the right client
                q = (
                    "DELETE FROM order_ "
                    "WHERE id = $1 AND client_id = $2"
                    "RETURNING id"
                )
                id_ = await conn.fetchval(q, order_id, client_id)
                if not id_:
                    raise

                flash(request, ("success", _("Votre commande a été supprimée.")))
        except Exception:
            flash(request, ("warning", _("Votre commande n'a pas pu être supprimée.")))
    return HTTPFound(request.app.router["list_order"].url_for())


@require("client")
@aiohttp_jinja2.template("list-order.html")
async def list_order(request):
    login = await authorized_userid(request)

    async with request.app["db-pool"].acquire() as conn:
        client = await conn.fetchrow(
            "SELECT id, disabled FROM client WHERE login = $1", login
        )

        q = (
            "SELECT CAST(o.id AS TEXT), o.date AS order_date, o.total, "
            "       b.date AS batch_date, "
            "       b.date - INTERVAL '12 hour' AS cancellation_date "
            "FROM order_ AS o "
            "INNER JOIN batch AS b ON o.batch_id = b.id "
            "WHERE o.client_id = $1 ORDER BY batch_date DESC"
        )
        orders = await conn.fetch(q, client["id"])
    return {"disabled": client["disabled"], "orders": orders, "now": datetime.now()}
